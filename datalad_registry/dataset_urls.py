import base64
import secrets
import time

from flask import Blueprint
from flask import jsonify
from flask import request
from flask import url_for

bp = Blueprint("dataset_urls", __name__, url_prefix="/v1/datasets/")

_TOKENS = {}  # token => {dsid, time_registered}
_TOKEN_TTL = 600


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
        # TODO: Need to periodically prune if this stays in memory.
        _TOKENS[token] = {"dsid": dsid,
                          "time_registered": time.time()}
        body = {"dsid": dsid,
                "url": url,
                "ref": "refs/datalad-registry/" + token,
                "token": token}
        headers = {"Cache-Control": f"max-age={_TOKEN_TTL}"}
        return jsonify(body), 200, headers


@bp.route("<uuid:dsid>/urls", methods=["GET", "POST"])
def urls(dsid):
    if request.method == "GET":
        # TODO: Retrieve URLs from database.
        return {"dsid": str(dsid),
                "urls": ["a", "b"]}
    elif request.method == "POST":
        data = request.json or {}
        try:
            token = data["token"]
            url = data["url"]
        except KeyError:
            # TODO: Do better validation.
            return jsonify(message="Invalid data"), 400

        token = data["token"]
        if token not in _TOKENS:
            return jsonify(message="Unknown token"), 400

        t_reg = _TOKENS[token]["time_registered"]
        if time.time() - t_reg < _TOKEN_TTL:
            # TODO: Register request.
            del _TOKENS[token]
            url_encoded = _url_encode(url)
            body = {"dsid": str(dsid),
                    "url": url_encoded}
            location = url_for(".urls", dsid=dsid) + "/" + url_encoded
            return jsonify(body), 202, {"Location": location}
        else:
            return jsonify(error="Expired token"), 410


@bp.route("<uuid:dsid>/urls/<string:url_encoded>")
def url(dsid, url_encoded):
    if request.method == "GET":
        # TODO: Query status.
        try:
            url = _url_decode(url_encoded)
        except base64.binascii.Error:
            return jsonify(message="Invalid encoded URL"), 400
        return jsonify(dsid=str(dsid), url=url, status="ok")
