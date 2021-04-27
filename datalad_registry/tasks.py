import logging
from pathlib import Path
import time

from datalad_registry import celery
from datalad_registry.models import db
from datalad_registry.models import URL
from datalad_registry.utils import url_encode

lgr = logging.getLogger(__name__)


def _extract_info_call_git(repo, commands):
    from datalad.support.exceptions import CommandError

    info = {}
    for name, command in commands.items():
        lgr.debug("Running %s in %s", command, repo)
        try:
            out = repo.call_git(command)
        except CommandError as exc:
            lgr.warning("Command %s in %s had non-zero exit code:\n%s",
                        command, repo, exc)
            continue
        info[name] = out.strip()
    return info


def _extract_git_info(repo):
    return _extract_info_call_git(
        repo,
        {"head": ["rev-parse", "--verify", "HEAD"],
         "head_describe": ["describe", "--tags"],
         "branches": ["for-each-ref", "--sort=-creatordate",
                      "--format=%(objectname) %(refname:lstrip=3)",
                      "refs/remotes/origin/"],
         "tags": ["for-each-ref", "--sort=-creatordate",
                  "--format=%(objectname) %(refname:lstrip=2)",
                  "refs/tags/"]})


def _extract_annex_info(repo):
    from datalad.support.exceptions import CommandError

    info = {}
    try:
        records = list(repo.call_annex_records(["info"], "origin"))
    except CommandError as exc:
        lgr.warning("Running `annex info` in %s had non-zero exit code:\n%s",
                    repo, exc)
    except AttributeError:
        lgr.debug("Skipping annex info collection for non-annex repo: %s",
                  repo)
    else:
        assert len(records) == 1, "bug: unexpected `annex info` output"
        res = records[0]
        info["annex_uuid"] = res["uuid"]
        info["annex_key_count"] = int(res["remote annex keys"])
    return info


@celery.task
def collect_dataset_info(datasets=None):
    """Collect information about `datasets`.

    Parameters
    ----------
    datasets : list of (<dataset ID>, <url>) tuples, optional
        If not specified, look for registered datasets that are not
        yet cloned or that have an announced update.
    """
    import datalad.api as dl
    from flask import current_app

    cache_dir = Path(current_app.config["DATALAD_REGISTRY_DATASET_CACHE"])
    cache_dir.mkdir(parents=True, exist_ok=True)

    ses = db.session
    if datasets is None:
        datasets = [(r.ds_id, r.url)
                    # Work on a few at a time, letting remaining be
                    # handled by next task.
                    #
                    # TODO: Think about better ways to handle this
                    # (here and for the update_announced query below).
                    for r in ses.query(URL).filter_by(info_ts=None).limit(3)]
        # TODO: Look at info_ts timestamp and refresh previous
        # information.
        if not datasets:
            datasets = [(r.ds_id, r.url)
                        for r in ses.query(URL).filter_by(update_announced=1)
                        .limit(3)]
    if not datasets:
        lgr.debug("Did not find URLs that needed information collected")
        return

    lgr.info("Collecting information for %s URLs", len(datasets))
    lgr.debug("Datasets: %s", datasets)

    for (ds_id, url) in datasets:
        ds_path = cache_dir / ds_id[:3] / url_encode(url)
        ds_path_str = str(ds_path)
        # TODO: Decide how to handle subdatasets.
        if ds_path.exists():
            ds = dl.Dataset(ds_path)
            ds_repo = ds.repo
            ds_repo.fetch(all_=True)
            ds_repo.call_git(["reset", "--hard", "refs/remotes/origin/HEAD"])
        else:
            ds = dl.clone(url, ds_path_str)
            ds_repo = ds.repo
        info = _extract_git_info(ds_repo)
        info.update(_extract_annex_info(ds_repo))
        info["info_ts"] = time.time()
        info["update_announced"] = 0
        db.session.query(URL).filter_by(url=url).update(info)
    db.session.commit()
