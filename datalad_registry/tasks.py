import logging
import subprocess as sp

from datalad_registry import celery
from datalad_registry.models import db
from datalad_registry.models import URL
from datalad_registry.models import Token

lgr = logging.getLogger(__name__)


@celery.task()
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
