"""Blueprint for /overview table view
"""

import logging

from flask import Blueprint, render_template, request
from sqlalchemy import nullslast, select

from datalad_registry.models import RepoUrl, db
from datalad_registry.search import parse_query

lgr = logging.getLogger(__name__)
bp = Blueprint("overview", __name__, url_prefix="/overview")

_SORT_ATTRS = {
    "keys-asc": ("annex_key_count", "asc"),
    "keys-desc": ("annex_key_count", "desc"),
    "update-asc": ("last_update_dt", "asc"),
    "update-desc": ("last_update_dt", "desc"),
    "url-asc": ("url", "asc"),
    "url-desc": ("url", "desc"),
    "annexed_files_in_wt_count-asc": ("annexed_files_in_wt_count", "asc"),
    "annexed_files_in_wt_count-desc": ("annexed_files_in_wt_count", "desc"),
    "annexed_files_in_wt_size-asc": ("annexed_files_in_wt_size", "asc"),
    "annexed_files_in_wt_size-desc": ("annexed_files_in_wt_size", "desc"),
    "git_objects_kb-asc": ("git_objects_kb", "asc"),
    "git_objects_kb-desc": ("git_objects_kb", "desc"),
}


@bp.get("/")
def overview():  # No type hints due to mypy#7187.
    default_sort_scheme = "update-desc"

    base_select_stmt = select(RepoUrl)

    # Search using query if provided.
    # ATM it is just a 'filter' on URL records, later might be more complex
    # as we would add search to individual files.
    query = request.args.get("query", None, type=str)
    search_error = None
    if query is not None:
        lgr.debug("Search by '%s'", query)
        try:
            criteria = parse_query(query)
        except Exception as e:
            search_error = str(e)
        else:
            base_select_stmt = base_select_stmt.filter(criteria)

    # Decipher sorting scheme
    sort_by = request.args.get("sort", default_sort_scheme, type=str)
    if sort_by not in _SORT_ATTRS:
        lgr.debug("Ignoring unknown sort parameter: %s", sort_by)
        sort_by = default_sort_scheme
    col, sort_method = _SORT_ATTRS[sort_by]

    # Apply sorting
    select_stmt = base_select_stmt.order_by(
        nullslast(getattr(getattr(RepoUrl, col), sort_method)())
    )

    # Paginate
    pagination = db.paginate(select_stmt)

    return render_template(
        "overview.html",
        pagination=pagination,
        sort_by=sort_by,
        search_query=query,
        search_error=search_error,
    )
