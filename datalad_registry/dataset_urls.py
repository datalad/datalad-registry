import base64
import secrets
import time

from flask import Blueprint
from flask import jsonify
from flask import request
from flask import url_for

from datalad_registry.db import get_db

bp = Blueprint("dataset_urls", __name__, url_prefix="/v1/datasets/")

_TOKEN_TTL = 600
_TOKEN_STATUSES = ["requested", "staged", "verified"]


def _url_decode(url):
    return base64.urlsafe_b64decode(url.encode()).decode()


def _url_encode(url):
    return base64.urlsafe_b64encode(url.encode()).decode()


@bp.route("<uuid:dsid>/urls/<string:url_encoded>/token")
def token(dsid, url_encoded):
    if request.method == "GET":
        try:
            url = _url_decode(url_encoded)
        except base64.binascii.Error:
            return jsonify(message="Invalid encoded URL"), 400

        token = secrets.token_hex(20)
        dsid = str(dsid)

        # TODO: Add separate script to prune old tokens.
        with get_db() as db:
            db.execute("INSERT INTO tokens VALUES (?, ?, ?, ?, 0)",
                       (token, dsid, url, time.time()))

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
        db = get_db()
        urls = [r["url"]
                for r in db.execute("SELECT url FROM dataset_urls "
                                    "WHERE dsid = ?",
                                    (dsid,))]
        return {"dsid": dsid, "urls": urls}
    elif request.method == "POST":
        data = request.json or {}
        try:
            token = data["token"]
            url = data["url"]
        except KeyError:
            # TODO: Do better validation.
            return jsonify(message="Invalid data"), 400

        db = get_db()
        row = db.execute(
            "SELECT ts FROM tokens "
            "WHERE token = ? AND url = ? AND dsid = ? AND status = 0",
            (token, url, dsid)).fetchone()
        if row is None:
            return jsonify(message="Unknown token"), 400

        if time.time() - row["ts"] < _TOKEN_TTL:
            # TODO: Set up background process that verifies the
            # challenge.
            with db:
                db.execute("UPDATE tokens SET status = 1 WHERE token = ?",
                           (token,))
            url_encoded = _url_encode(url)
            body = {"dsid": dsid,
                    "url": url_encoded}
            location = url_for(".urls", dsid=dsid) + "/" + url_encoded
            return jsonify(body), 202, {"Location": location}
        else:
            return jsonify(error="Expired token"), 410


@bp.route("<uuid:dsid>/urls/<string:url_encoded>")
def url(dsid, url_encoded):
    if request.method == "GET":
        dsid = str(dsid)
        try:
            url = _url_decode(url_encoded)
        except base64.binascii.Error:
            return jsonify(message="Invalid encoded URL"), 400

        db = get_db()
        row_known = db.execute(
            "SELECT url FROM dataset_urls "
            "WHERE url = ? AND dsid = ? LIMIT 1",
            url, dsid).fetchone()
        if row_known is None:
            status = "unknown"
            row_tok = db.execute(
                "SELECT MAX(status) as max_status FROM tokens "
                "WHERE url = ? AND dsid = ?",
                url, dsid).fetchone()
            if row_tok["max_status"] is not None:
                status = _TOKEN_STATUSES[int(row_tok["max_status"])]
        else:
            status = "known"

        return jsonify(dsid=dsid, url=url, status=status)