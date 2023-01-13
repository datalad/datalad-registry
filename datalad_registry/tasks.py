from datetime import datetime, timezone
import errno
import logging
from pathlib import Path
from shutil import rmtree
from typing import Any, Dict, List, Optional, Tuple, Union

from datalad_registry import celery
from datalad_registry.models import URL, db
from datalad_registry.utils import url_encode

lgr = logging.getLogger(__name__)

InfoType = Dict[str, Union[str, float, datetime]]


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
        ds = dl.clone(url, ds_path_str)
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
            "head_describe": ["describe", "--tags"],
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
        info['annexed_files_in_wt_size'] = int(
            working_tree_record['size of annexed files in working tree']
        )

    return info


@celery.task
def collect_dataset_uuid(url: str) -> None:
    from flask import current_app

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
    abbrev_id = "None" if ds_id is None else ds_id[:3]
    try:
        ds_path.rename(cache_dir / abbrev_id / url_encode(url))
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
    db.session.commit()


@celery.task
def collect_dataset_info(datasets: Optional[List[Tuple[str, str]]] = None) -> None:
    """Collect information about `datasets`.

    Parameters
    ----------
    datasets : list of (<dataset ID>, <url>) tuples, optional
        If not specified, look for registered datasets that have an
        announced update.
    """

    from flask import current_app

    cache_dir = Path(current_app.config["DATALAD_REGISTRY_DATASET_CACHE"])
    cache_dir.mkdir(parents=True, exist_ok=True)

    ses = db.session
    if datasets is None:
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

    # TODO: this should be done by celery! it is silly to do it sequentially
    # here.  I guess they might need to be groupped by ds_id since the same
    # cache location is to be reused - each task should then handle it
    for (ds_id, url) in datasets:
        abbrev_id = "None" if ds_id is None else ds_id[:3]
        ds_path = cache_dir / abbrev_id / url_encode(url)
        ds = clone_dataset(url, ds_path)
        info = get_info(ds.repo)
        if ds_id is None:
            info["ds_id"] = ds.id
        elif ds_id != ds.id:
            lgr.warning("A dataset with an ID (%s) got a new one (%s)", ds_id, ds.id)
        info["processed"] = True
        # TODO: check if ds_id is still the same. If changed -- create a new
        # entry for it?
        db.session.query(URL).filter_by(url=url).update(info)
    db.session.commit()
