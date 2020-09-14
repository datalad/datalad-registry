import logging
import subprocess as sp

from datalad_registry import celery
from datalad_registry import db
from datalad_registry.utils import TokenStatus

lgr = logging.getLogger(__name__)


@celery.task()
def verify_url(dsid, url, token):
    """Check that `url` has a challenge reference for `token`.
    """
    exists = db.read("SELECT * FROM dataset_urls WHERE url = ? AND dsid = ?",
                     url, dsid).fetchone()
    if exists:
        status = TokenStatus.NOTNEEDED
    else:
        try:
            sp.check_call(["git", "ls-remote", "--quiet", "--exit-code",
                           url, "refs/datalad-registry/" + token])
        except sp.CalledProcessError as exc:
            lgr.info("Failed to verify status %s at %s: %s",
                     dsid, url, exc)
            status = TokenStatus.FAILED
        else:
            status = TokenStatus.VERIFIED
            db.write("INSERT INTO dataset_urls VALUES (?, ?)",
                     url, dsid)
    db.write("UPDATE tokens SET status = ? WHERE token = ?",
             status, token)
