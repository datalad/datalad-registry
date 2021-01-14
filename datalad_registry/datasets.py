"""Blueprint for /datasets view
"""

import logging

from flask import Blueprint
from flask import request

from datalad_registry.models import db
from datalad_registry.models import URL

lgr = logging.getLogger(__name__)
bp = Blueprint("datasets", __name__, url_prefix="/v1/")


@bp.route("datasets")
def datasets():
    if request.method == "GET":
        lgr.info("Getting list of known datasets")
        r = db.session.query(URL.dsid).group_by(URL.dsid)
        r = r.order_by(URL.dsid.asc())
        return {"dsids": [i.dsid for i in r]}
