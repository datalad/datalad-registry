"""Blueprint for /
"""
import logging

from flask import Blueprint, redirect, url_for
from werkzeug.wrappers import Response

lgr = logging.getLogger(__name__)
bp = Blueprint("root", __name__, url_prefix="")


@bp.get("/")
def root() -> Response:
    return redirect(url_for("overview.overview"))
