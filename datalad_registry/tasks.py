from datetime import datetime, timezone
import errno
import logging
from pathlib import Path
from shutil import rmtree
from typing import Any, Dict, List, Optional, Tuple, Union

from celery import group
from datalad import api as dl
from datalad.support.exceptions import IncompleteResultsError
from pydantic import StrictStr, parse_obj_as, validate_arguments

from datalad_registry import celery
from datalad_registry.models import URL, URLMetadata, db
from datalad_registry.utils.url_encoder import url_encode

from .com_models import MetaExtractResult

lgr = logging.getLogger(__name__)

InfoType = Dict[str, Union[str, float, datetime]]


# todo: The value of url is encoded in ds_path, so we have passed it twice to this func.
#       Find a way to remove this redundancy.
def clone_dataset(url: str, ds_path: Path) -> Any:
    import datalad.api as dl

    ds_path_str = str(ds_path)
    # TODO (later): Decide how to handle subdatasets.
    # TODO: support multiple URLs/remotes per dataset
    # Make remote name to be a hash of url. Check below if among
    # remotes and add one if missing, then use that remote, not 'origin'
    if ds_path.exists():
        ds = dl.Dataset(ds_path)
        ds_repo = ds.repo
        ds_repo.fetch(all_=True)
        ds_repo.call_git(["reset", "--hard", "refs/remotes/origin/HEAD"])
    else:
        max_incomplete_results_errs = 5
        incomplete_results_err_count = 0

        # Clone the dataset @ url into ds_path
        while True:
            try:
                ds = dl.clone(url, ds_path_str)
            except Exception as e:
                # If failed cloning attempt created a directory, remove it
                if ds_path.exists():
                    rmtree(ds_path)

                if isinstance(e, IncompleteResultsError):
                    lgr.warning(
                        f"IncompleteResultsError in cloning {url}. Trying again."
                    )

                    incomplete_results_err_count += 1
                    if incomplete_results_err_count > max_incomplete_results_errs:
                        raise
                else:
                    raise
            else:
                break

    return ds


def get_info(ds_repo: Any) -> InfoType:
    info: InfoType = _extract_git_info(ds_repo)
    info.update(_extract_annex_info(ds_repo))
    info["info_ts"] = datetime.now(timezone.utc)
    info["update_announced"] = False
    info["git_objects_kb"] = ds_repo.count_objects["size"]
    return info


# NOTE: A type isn't specified for repo using a top-level DataLad
# import leads to an asyncio-related error: "RuntimeError: Cannot add
# child handler, the child watcher does not have a loop attached".


def _extract_info_call_git(repo, commands: Dict[str, List[str]]) -> InfoType:
    from datalad.support.exceptions import CommandError

    info = {}
    for name, command in commands.items():
        lgr.debug("Running %s in %s", command, repo)
        try:
            out = repo.call_git(command)
        except CommandError as exc:
            lgr.warning(
                "Command %s in %s had non-zero exit code:\n%s", command, repo, exc
            )
            continue
        info[name] = out.strip()
    return info


def _extract_git_info(repo) -> InfoType:
    return _extract_info_call_git(
        repo,
        {
            "head": ["rev-parse", "--verify", "HEAD"],
            "head_describe": ["describe", "--tags", "--always"],
            "branches": [
                "for-each-ref",
                "--sort=-creatordate",
                "--format=%(objectname) %(refname:lstrip=3)",
                "refs/remotes/origin/",
            ],
            "tags": [
                "for-each-ref",
                "--sort=-creatordate",
                "--format=%(objectname) %(refname:lstrip=2)",
                "refs/tags/",
            ],
        },
    )


def _extract_annex_info(repo) -> InfoType:
    from datalad.support.exceptions import CommandError

    info = {}
    try:
        origin_records = repo.call_annex_records(["info"], "origin")
        working_tree_records = repo.call_annex_records(["info", "--bytes"])
    except CommandError as exc:
        lgr.warning("Running `annex info` in %s had non-zero exit code:\n%s", repo, exc)
    except AttributeError:
        lgr.debug("Skipping annex info collection for non-annex repo: %s", repo)
    else:
        assert len(origin_records) == 1, "bug: unexpected `annex info` output"
        assert len(working_tree_records) == 1, "bug: unexpected `annex info` output"

        origin_record = origin_records[0]
        working_tree_record = working_tree_records[0]

        info["annex_uuid"] = origin_record["uuid"]
        info["annex_key_count"] = int(origin_record["remote annex keys"])

        info["annexed_files_in_wt_count"] = working_tree_record[
            "annexed files in working tree"
        ]
        info["annexed_files_in_wt_size"] = int(
            working_tree_record["size of annexed files in working tree"]
        )

    return info


@celery.task
@validate_arguments
def collect_dataset_uuid(url: str) -> None:
    from flask import current_app

    # todo: This can possibly done in the setup of the app
    #       not as part of an individual task.
    cache_dir = Path(current_app.config["DATALAD_REGISTRY_DATASET_CACHE"])
    cache_dir.mkdir(parents=True, exist_ok=True)

    lgr.info("Collecting UUIDs for URL %s", url)

    result = db.session.query(URL).filter_by(url=url)
    # r = result.first()
    # assert r is not None
    # assert not r.processed
    # assert r.ds_id is None
    ds_path = cache_dir / "UNKNOWN" / url_encode(url)
    ds = clone_dataset(url, ds_path)
    ds_id = ds.id
    info = get_info(ds.repo)
    info["ds_id"] = ds_id
    info["processed"] = True
    result.update(info)

    # todo: This definition of abbrev_id and the target of the rename is problematic.
    #       For example, if overtime one single url store two different datasets
    #       each has an UUID that starts with the same 3 characters, then you have
    #       a problem of handling the wrong dataset.

    abbrev_id = "None" if ds_id is None else ds_id[:3]

    # Ensure the existence of the containing directory of
    # the destination of the cloned dataset
    cache_dir_level1 = cache_dir / abbrev_id
    cache_dir_level1.mkdir(parents=True, exist_ok=True)

    try:
        ds_path.rename(cache_dir_level1 / url_encode(url))
    except OSError as e:
        if e.errno == errno.ENOTEMPTY:
            lgr.debug("Clone of %s already in cache", url)
        else:
            lgr.exception(
                "Error moving dataset for %s to %s directory in cache",
                url,
                abbrev_id,
            )
        rmtree(ds_path)
    # todo: marking of problematic code ends

    db.session.commit()


# todo: It is not very clear why the UUID of a dataset  has to be provided.
#       By having this piece of information provided by the user, we are exposed to the
#       risk of the user providing a wrong UUID.
@celery.task
@validate_arguments
def collect_dataset_info(
    datasets: Optional[List[Tuple[StrictStr, StrictStr]]] = None
) -> None:
    """Collect information about `datasets`.

    Parameters
    ----------
    datasets : list of (<dataset ID>, <url>) tuples, optional
        If not specified, look for registered datasets that have an
        announced update.
    """

    ses = db.session
    if datasets is None:
        # todo: If this case is intended to be done in celery's beat/corn,
        #       then this case should be organized as an independent task.
        # this one is done on celery's beat/cron
        # TODO: might "collide" between announced update (datasets is provided)
        # and cron.  How can we lock/protect?
        # see https://github.com/datalad/datalad-registry/issues/34 which might
        # be manifestation of absent protection/support for concurrency
        datasets = [
            (r.ds_id, r.url)
            for r in ses.query(URL).filter_by(update_announced=True)
            # TODO: get all, group by id, send individual tasks
            # Q: could multiple instances of this task be running
            # at the same time????
            # TODO: if no updates, still do some randomly
            .limit(3)
        ]

    if not datasets:
        lgr.debug("Did not find URLs that needed information collected")
        return

    lgr.info("Collecting information for %s URLs", len(datasets))
    lgr.debug("Datasets: %s", datasets)

    # Update the information about the urls in the database in parallel
    group(update_url_info.s(ds_id, url) for (ds_id, url) in set(datasets))()


@celery.task
def update_url_info(ds_id: str, url: str) -> None:
    """
    Update the information about a URL of a dataset in the database

    :param ds_id: The given UUID of the dataset
    :param url: The URL of a copy/clone of a dataset
    """
    from flask import current_app

    # todo: This can possibly done in the setup of the app
    #       not as part of an individual task.
    cache_dir = Path(current_app.config["DATALAD_REGISTRY_DATASET_CACHE"])
    cache_dir.mkdir(parents=True, exist_ok=True)  # This seems to be safe in parallel

    # todo: This definition of abbrev_id and the target of the rename is problematic.
    #       For example, if overtime one single url store two different datasets
    #       each has an UUID that starts with the same 3 characters, then you have
    #       a problem of handling the wrong dataset.
    abbrev_id = "None" if ds_id is None else ds_id[:3]
    ds_path = cache_dir / abbrev_id / url_encode(url)
    ds = clone_dataset(url, ds_path)
    info = get_info(ds.repo)
    if ds_id is None:
        info["ds_id"] = ds.id
    elif ds_id != ds.id:
        lgr.warning("A dataset with an ID (%s) got a new one (%s)", ds_id, ds.id)
        # todo: The value of ds_id must be incorrect. Handle it.
        #       Possibly doing the following
        #       info["ds_id"] = ds.id
        #       rename the cache directory

    info["processed"] = True
    # TODO: check if ds_id is still the same. If changed -- create a new
    # entry for it?

    session = db.session
    session.query(URL).filter_by(url=url).update(info)
    session.commit()


@celery.task
def extract_meta(url_id: int, dataset_path: str, extractor: str) -> bool:
    """
    Extract dataset level metadata from a dataset

    :param url_id: The ID (primary key) of the URL of the dataset in the database
    :param dataset_path: The path to the dataset in the local cache
    :param extractor: The name of the extractor to use
    :return: True if the extractor has produced metadata and the metadata has been
             recorded to the database; False otherwise.
    """
    url = db.session.execute(db.select(URL).where(URL.id == url_id)).scalar_one()

    results = parse_obj_as(
        list[MetaExtractResult],
        dl.meta_extract(
            extractor,
            dataset=dataset_path,
            result_renderer="disabled",
            on_failure="stop",
        ),
    )

    if len(results) == 0:
        lgr.debug(
            "Extractor %s did not produce any metadata for %s", extractor, url.url
        )
        return False

    produced_valid_result = False
    for res in results:
        if res.status != "ok":
            lgr.debug(
                "A result of extractor %s for %s is not 'ok'."
                "It will not be recorded to the database",
                extractor,
                url.url,
            )
        else:
            # Record the metadata to the database
            metadata_record = res.metadata_record
            url_metadata = URLMetadata(
                dataset_describe=url.head_describe,
                dataset_version=metadata_record.dataset_version,
                extractor_name=metadata_record.extractor_name,
                extractor_version=metadata_record.extractor_version,
                extraction_parameter=metadata_record.extraction_parameter,
                extracted_metadata=metadata_record.extracted_metadata,
                url=url,
            )
            db.session.add(url_metadata)

            produced_valid_result = True

    if produced_valid_result:
        db.session.commit()
        return True
    else:
        return False
