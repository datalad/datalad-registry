"""Blueprint for /datasets/<ds_id>/urls views

Each function here has a corresponding path in docs/openapi.yml with
the operationId dataset_urls.{function_name}.{request_method}.
"""

import logging
from typing import Any

from flask import Blueprint
from flask import jsonify
from flask import request

from datalad_registry import tasks
from datalad_registry.models import db
from datalad_registry.models import URL
from datalad_registry.utils import InvalidURL
from datalad_registry.utils import url_decode

lgr = logging.getLogger(__name__)
bp = Blueprint("dataset_urls", __name__, url_prefix="/v1/datasets/")

# See mypy#7187 for why Any is used for return value.


@bp.route("<uuid:ds_id>/urls")
def urls(ds_id: str) -> Any:
    ds_id = str(ds_id)
    if request.method == "GET":
        lgr.info("Reporting which URLs are registered for %s", ds_id)
        urls = [r.url
                for r in db.session.query(URL).filter_by(ds_id=ds_id)]
        return jsonify(ds_id=ds_id, urls=urls)


@bp.route("<uuid:ds_id>/urls/<string:url_encoded>", methods=["GET", "PATCH"])
def url(ds_id: str, url_encoded: str) -> Any:
    ds_id = str(ds_id)
    try:
        url = url_decode(url_encoded)
    except InvalidURL:
        return jsonify(message="Invalid encoded URL"), 400

    result = db.session.query(URL).filter_by(url=url, ds_id=ds_id)
    row_known = result.first()

    if request.method == "GET":
        lgr.info("Checking status of registering %s as URL of %s",
                 url, ds_id)
        resp: Any = {"ds_id": ds_id, "url": url}
        if row_known is None:
            status = "unknown"
        else:
            status = "known"
            resp["info"] = {
                col: getattr(row_known, col, None)
                for col in ["annex_uuid", "annex_key_count",
                            "head", "head_describe"]}

        lgr.debug("Status for %s: %s", url, status)
        resp["status"] = status
        return jsonify(resp)
    elif request.method == "PATCH":
        if row_known is None:
            db.session.add(URL(ds_id=ds_id, url=url))
            db.session.commit()
            tasks.collect_dataset_info.delay([(ds_id, url)])
        else:
            result.update({"update_announced": 1})
            db.session.commit()
        return "", 202
