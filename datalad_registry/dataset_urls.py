"""Blueprint for /datasets/<ds_id>/urls views

Each function here has a corresponding path in docs/openapi.yml with
the operationId dataset_urls.{function_name}.{request_method}.
"""

import logging
from typing import Any

from flask import Blueprint, jsonify, request

from datalad_registry import tasks
from datalad_registry.models import URL, db
from datalad_registry.utils.url_encoder import InvalidURL, url_decode

lgr = logging.getLogger(__name__)
bp = Blueprint("dataset_urls", __name__, url_prefix="/v1/datasets/")

# See mypy#7187 for why Any is used for return value.


@bp.get("<uuid:ds_id>/urls")
def urls(ds_id: str) -> Any:
    ds_id = str(ds_id)

    lgr.info("Reporting which URLs are registered for %s", ds_id)
    urls = [r.url for r in db.session.query(URL).filter_by(ds_id=ds_id)]
    return jsonify(ds_id=ds_id, urls=urls)


@bp.route("<uuid:ds_id>/urls/<string:url_encoded>", methods=["GET", "PATCH"])
def url(ds_id: str, url_encoded: str) -> Any:
    ds_id = str(ds_id)
    try:
        url = url_decode(url_encoded)
    except InvalidURL:
        return jsonify(message="Invalid encoded URL"), 400

    result = db.session.query(URL).filter_by(url=url)
    # even here could lead to sqlite locking issue, I guess if
    # collect_dataset_info is in progress:
    # https://github.com/datalad/datalad-registry/issues/34
    row_known = result.first()

    # We can't replace this check by adding `ds_id=ds_id` to the filter query,
    # as then entries without ds_id set would not be returned, as though they
    # were unregistered, leading to PATCH requests trying to register the URLs
    # again by adding a row to the database, causing an error.
    if row_known is not None and row_known.ds_id != ds_id:
        # TODO: figure out/provide logic/responses for datasets/urls which get
        # their .id changed, or yet to be processed (i.e. `not
        # row_known.processed`)
        return jsonify(message="UUID does not match value registered for URL"), 400

    if request.method == "GET":
        lgr.info("Checking status of registering %s as URL of %s", url, ds_id)
        resp: dict = {"ds_id": ds_id, "url": url}
        if row_known is None:
            status = "unknown"
        elif not row_known.processed:
            status = "unprocessed"
        else:
            status = "known"
            resp["info"] = {
                col: getattr(row_known, col, None)
                for col in ["annex_uuid", "annex_key_count", "head", "head_describe"]
            }

        lgr.debug("Status for %s: %s", url, status)
        resp["status"] = status
        return jsonify(resp)
    elif request.method == "PATCH":
        if row_known is None:
            # todo: This is problematic for there is no guarantee that the dataset
            #       at the url given in the request actually has a dataset id that is
            #       ds_id given in the request. In fact, there is no guarantee that the
            #       url given at the request is indeed the url of a dataset at all.
            db.session.add(URL(ds_id=ds_id, url=url))
            db.session.commit()
            tasks.collect_dataset_info.delay([(ds_id, url)])
        elif row_known.processed:
            # todo: Is the intended statement
            #       row_known.update({"update_announced": True})
            #       ?
            result.update({"update_announced": True})
            db.session.commit()
        return "", 202
