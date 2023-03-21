from flask import Blueprint

bp = Blueprint("api", __name__)

# Ignoring flake8 rules in the following import.
# F401: imported but unused
# E402: module level import not at top of file
# Attach URL metadata related API endpoints
from . import url_metadata  # noqa: F401, E402