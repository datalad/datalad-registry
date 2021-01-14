"""Blueprint for /datasets view
"""

import logging

from flask import Blueprint
from flask import request
from flask import url_for

from datalad_registry.models import db
from datalad_registry.models import URL

lgr = logging.getLogger(__name__)
bp = Blueprint("datasets", __name__, url_prefix="/v1/")

_PAGE_NITEMS = 100  # TODO: Should eventually be configurable by app.


@bp.route("datasets")
def datasets():
    if request.method == "GET":
        lgr.info("Getting list of known datasets")
        r = db.session.query(URL.dsid).group_by(URL.dsid)
        r = r.order_by(URL.dsid.asc())
        r = r.paginate(request.args.get('page', 1, type=int),
                       _PAGE_NITEMS, False)
        # TODO: Eventually switch over to using _external=True so that
        # caller doesn't need to construct URL?
        pg_n = url_for(".datasets", page=r.next_num) if r.has_next else None
        pg_p = url_for(".datasets", page=r.prev_num) if r.has_prev else None
        return {"next": pg_n,
                "previous": pg_p,
                "dsids": [i.dsid for i in r.items]}
