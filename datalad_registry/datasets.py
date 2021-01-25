"""Blueprint for /datasets view
"""

import logging

from flask import Blueprint
from flask import jsonify
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
        r = db.session.query(URL.ds_id).group_by(URL.ds_id)
        r = r.order_by(URL.ds_id.asc())
        r = r.paginate(request.args.get('page', 1, type=int),
                       _PAGE_NITEMS, False)
        # TODO: Eventually switch over to using _external=True so that
        # caller doesn't need to construct URL?
        pg_n = url_for(".datasets", page=r.next_num) if r.has_next else None
        pg_p = url_for(".datasets", page=r.prev_num) if r.has_prev else None
        return jsonify({"next": pg_n,
                        "previous": pg_p,
                        "ds_ids": [i.ds_id for i in r.items]})
