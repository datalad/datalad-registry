"""Blueprint for root view
"""

import logging
from typing import Any

from flask import Blueprint, jsonify, request, url_for

from datalad_registry import tasks
from datalad_registry.models import URL, db
from datalad_registry.utils import InvalidURL, url_decode

lgr = logging.getLogger(__name__)
bp = Blueprint("datasets", __name__, url_prefix="/v1/")

_PAGE_NITEMS = 100  # TODO: Should eventually be configurable by app.


@bp.route("datasets")
def datasets():  # No type hints due to mypy#7187.
    if request.method == "GET":
        lgr.info("Getting list of known datasets")
        r = db.session.query(URL.ds_id).group_by(URL.ds_id)
        r = r.order_by(URL.ds_id.asc())
        r = r.paginate(page=request.args.get("page", 1, type=int),
                       per_page=_PAGE_NITEMS,
                       error_out=False)
        # TODO: Eventually switch over to using _external=True so that
        # caller doesn't need to construct URL?
        pg_n = url_for(".datasets", page=r.next_num) if r.has_next else None
        pg_p = url_for(".datasets", page=r.prev_num) if r.has_prev else None
        return jsonify(
            {"next": pg_n, "previous": pg_p, "ds_ids": [i.ds_id for i in r.items]}
        )


@bp.route("urls/<string:url_encoded>", methods=["GET", "PATCH"])
def urls(url_encoded: str) -> Any:
    try:
        url = url_decode(url_encoded)
    except InvalidURL:
        return jsonify(message="Invalid encoded URL"), 400

    result = db.session.query(URL).filter_by(url=url)
    row_known = result.first()

    if request.method == "GET":
        lgr.info("Checking status of registering %s as URL", url)
        resp: dict = {"url": url}
        if row_known is None:
            status = "unknown"
        elif not row_known.processed:
            status = "unprocessed"
        else:
            status = "known"
            resp["ds_id"] = row_known.ds_id
            resp["info"] = {
                col: getattr(row_known, col, None)
                for col in ["annex_uuid", "annex_key_count", "head", "head_describe"]
            }
        lgr.debug("Status for %s: %s", url, status)
        resp["status"] = status
        return jsonify(resp)

    elif request.method == "PATCH":
        if row_known is None:
            db.session.add(URL(url=url))
            db.session.commit()
            tasks.collect_dataset_uuid.delay(url)
        elif row_known.processed:
            result.update({"update_announced": True})
            db.session.commit()
        return "", 202
