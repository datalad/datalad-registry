import logging
from pathlib import Path
import subprocess as sp
import time

from datalad_registry import celery
from datalad_registry.models import db
from datalad_registry.models import URL
from datalad_registry.models import Token
from datalad_registry.utils import url_encode

lgr = logging.getLogger(__name__)


@celery.task
def verify_url(ds_id, url, token):
    """Check that `url` has a challenge reference for `token`.
    """
    exists = db.session.query(URL).filter_by(
        url=url, ds_id=ds_id).one_or_none()
    if exists:
        status = Token.status_enum.NOTNEEDED
    else:
        try:
            sp.check_call(["git", "ls-remote", "--quiet", "--exit-code",
                           url, "refs/datalad-registry/" + token])
        except sp.CalledProcessError as exc:
            lgr.info("Failed to verify status %s at %s: %s",
                     ds_id, url, exc)
            status = Token.status_enum.FAILED
        else:
            status = Token.status_enum.VERIFIED
            db.session.add(URL(ds_id=ds_id, url=url))
    db.session.query(Token).filter_by(token=token).update(
        {"status": status})
    db.session.commit()


@celery.task
def prune_old_tokens(cutoff=None):
    """Remove old tokens from the database.

    Parameters
    ----------
    cutoff : int, optional
        Remove tokens with a timestamp (seconds since the Epoch)
        earlier than this value.  By default, a timestamp
        corresponding to ten days before the current time is used.
    """
    if cutoff is None:
        cutoff = time.time() - 864000  # 10 days ago
    lgr.info("Pruning tokens before %s from %s", cutoff, db)
    db.session.query(Token).filter(Token.ts < cutoff).delete()
    db.session.commit()


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
def collect_dataset_info(urls=None):
    """Collect information about the dataset at each URL in `urls`.
    """
    import datalad.api as dl
    from flask import current_app

    cache_dir = Path(current_app.config["DATALAD_REGISTRY_DATASET_CACHE"])
    cache_dir.mkdir(parents=True, exist_ok=True)

    ses = db.session
    if urls is None:
        urls = [r.url
                # Work on a few at a time, letting remaining be
                # handled by next task.
                #
                # TODO: Think about better ways to handle this (here
                # and for the update_announced query below).
                for r in ses.query(URL).filter_by(info_ts=None).limit(3)]
        # TODO: Look at info_ts timestamp and refresh previous
        # information.
        if not urls:
            urls = [r.url
                    for r in ses.query(URL).filter_by(update_announced=1)
                    .limit(3)]
    if not urls:
        lgr.debug("Did not find URLs that needed information collected")
        return

    lgr.info("Collecting information for %s URLs", len(urls))
    lgr.debug("URLs: %s", urls)

    for url in urls:
        ds_path = cache_dir / url_encode(url)
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
