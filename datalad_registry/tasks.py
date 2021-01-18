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


def _extract_git_info(path):
    commands = {
        "head": ["git", "rev-parse", "--verify", "HEAD"],
        "head_describe": ["git", "describe", "--tags"],
        "branches": ["git", "for-each-ref", "--sort=-creatordate",
                     "--format=%(objectname) %(refname:lstrip=2)",
                     "refs/heads/"],
        "tags": ["git", "for-each-ref", "--sort=-creatordate",
                 "--format=%(objectname) %(refname:lstrip=2)",
                 "refs/tags/"],
    }
    info = {}
    for name, command in commands.items():
        lgr.debug("Running %s in %s", command, path)
        res = sp.run(command,
                     cwd=path, universal_newlines=True, capture_output=True)
        if res.returncode == 0:
            info[name] = res.stdout.strip()
        else:
            lgr.warning("Command %s in %s had non-zero exit code: %s"
                        "\nstderr: %s",
                        command, path, res.returncode, res.stderr)
    return info


@celery.task
def collect_git_info(urls=None):
    """Collect basic information about the Git repo at each URL in `urls`.
    """
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
        # TODO: Assuming the same clone is used to collect information
        # with datalad, need to switch away from mirroring.
        if ds_path.exists():
            sp.run(["git", "fetch"], cwd=str(ds_path))
        else:
            sp.run(["git", "clone", "--mirror", "--template=",
                    url, str(ds_path)])

        info = _extract_git_info(str(ds_path))
        info["info_ts"] = time.time()
        info["update_announced"] = 0
        db.session.query(URL).filter_by(url=url).update(info)
    db.session.commit()
