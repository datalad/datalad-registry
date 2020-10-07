import logging
import subprocess as sp
import time

from datalad_registry import celery
from datalad_registry.models import db
from datalad_registry.models import URL
from datalad_registry.models import Token

lgr = logging.getLogger(__name__)


@celery.task
def verify_url(dsid, url, token):
    """Check that `url` has a challenge reference for `token`.
    """
    exists = db.session.query(URL).filter_by(
        url=url, dsid=dsid).one_or_none()
    if exists:
        status = Token.status_enum.NOTNEEDED
    else:
        try:
            sp.check_call(["git", "ls-remote", "--quiet", "--exit-code",
                           url, "refs/datalad-registry/" + token])
        except sp.CalledProcessError as exc:
            lgr.info("Failed to verify status %s at %s: %s",
                     dsid, url, exc)
            status = Token.status_enum.FAILED
        else:
            status = Token.status_enum.VERIFIED
            db.session.add(URL(dsid=dsid, url=url))
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
