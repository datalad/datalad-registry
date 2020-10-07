"""Blueprint for /datasets/<dsid>/urls views

Each function here has a corresponding path in docs/openapi.yml with
the operationId dataset_urls.{function_name}.{request_method}.
"""

import logging
import secrets
import time

from flask import Blueprint
from flask import jsonify
from flask import request
from flask import url_for
import sqlalchemy as sa

from datalad_registry import tasks
from datalad_registry.models import db
from datalad_registry.models import Token
from datalad_registry.models import URL

from datalad_registry.utils import InvalidURL
from datalad_registry.utils import url_decode
from datalad_registry.utils import url_encode

lgr = logging.getLogger(__name__)
bp = Blueprint("dataset_urls", __name__, url_prefix="/v1/datasets/")

_TOKEN_TTL = 600


@bp.route("<uuid:dsid>/urls/<string:url_encoded>/token")
def token(dsid, url_encoded):
    if request.method == "GET":
        try:
            url = url_decode(url_encoded)
        except InvalidURL:
            return jsonify(message="Invalid encoded URL"), 400

        token = secrets.token_hex(20)
        dsid = str(dsid)
        lgr.info("Generated token %s for %s => %s", token, url, dsid)

        db.session.add(
            Token(token=token, dsid=dsid, url=url, ts=time.time(), status=0))
        db.session.commit()

        body = {"dsid": dsid,
                "url": url,
                "ref": "refs/datalad-registry/" + token,
                "token": token}
        headers = {"Cache-Control": f"max-age={_TOKEN_TTL}"}
        return jsonify(body), 200, headers


@bp.route("<uuid:dsid>/urls", methods=["GET", "POST"])
def urls(dsid):
    dsid = str(dsid)
    if request.method == "GET":
        lgr.info("Reporting which URLs are registered for %s", dsid)
        urls = [r.url
                for r in db.session.query(URL).filter_by(dsid=dsid)]
        return {"dsid": dsid, "urls": urls}
    elif request.method == "POST":
        data = request.json or {}
        try:
            token = data["token"]
            url = data["url"]
        except KeyError:
            # TODO: Do better validation.
            return jsonify(message="Invalid data"), 400
        row = db.session.query(Token).filter_by(
            token=token, url=url, dsid=dsid,
            status=Token.status_enum.REQUESTED).first()
        if row is None:
            return jsonify(message="Unknown token"), 400

        if time.time() - row.ts < _TOKEN_TTL:
            db.session.query(Token).filter_by(token=token).update(
                {"status": Token.status_enum.STAGED})
            db.session.commit()
            tasks.verify_url.delay(dsid, url, token)
            url_encoded = url_encode(url)
            body = {"dsid": dsid,
                    "url_encoded": url_encoded}
            location = url_for(".urls", dsid=dsid) + "/" + url_encoded
            return jsonify(body), 202, {"Location": location}
        else:
            return jsonify(message="Expired token"), 410


@bp.route("<uuid:dsid>/urls/<string:url_encoded>")
def url(dsid, url_encoded):
    if request.method == "GET":
        dsid = str(dsid)
        try:
            url = url_decode(url_encoded)
        except InvalidURL:
            return jsonify(message="Invalid encoded URL"), 400

        lgr.info("Checking status of registering %s as URL of %s",
                 url, dsid)
        row_known = db.session.query(URL).filter_by(
            url=url, dsid=dsid).first()
        if row_known is None:
            status = "unknown"
            max_status, = db.session.query(
                sa.func.max(Token.status)).filter_by(
                    url=url, dsid=dsid).first()
            if max_status is not None:
                status = Token.describe_status(max_status)
        else:
            status = "known"

        lgr.debug("Status for %s: %s", url, status)
        return jsonify(dsid=dsid, url=url, status=status)
