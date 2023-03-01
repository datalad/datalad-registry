"""Blueprint for /overview table view
"""

import logging

from flask import Blueprint, render_template, request

from datalad_registry.models import URL, db

lgr = logging.getLogger(__name__)
bp = Blueprint("overview", __name__, url_prefix="/overview")

_PAGE_NITEMS = 25  # TODO: Should eventually be configurable by app.
_SORT_ATTRS = {
    "keys-asc": ("annex_key_count", "asc"),
    "keys-desc": ("annex_key_count", "desc"),
    "update-asc": ("info_ts", "asc"),
    "update-desc": ("info_ts", "desc"),
    "url-asc": ("url", "asc"),
    "url-desc": ("url", "desc"),
}

# Columns of the table displayed on the overview page
_COLS = [
    "ds_id",
    "url",
    "annex_key_count",
    "head",
    "head_describe",
    "annexed_files_in_wt_count",
    "annexed_files_in_wt_size",
    "git_objects_kb",
]


@bp.get("/")
def overview():  # No type hints due to mypy#7187.
    r = db.session.query(URL)
    url_filter = request.args.get("filter", None, type=str)
    if url_filter:
        lgr.debug("Filter URLs by '%s'", url_filter)
        r = r.filter(URL.url.contains(url_filter, autoescape=True))

    r = r.group_by(URL)
    sort_by = request.args.get("sort", "update-desc", type=str)
    if sort_by not in _SORT_ATTRS:
        lgr.debug("Ignoring unknown sort parameter: %s", sort_by)
        sort_by = "update-desc"
    col, sort_method = _SORT_ATTRS[sort_by]

    r = r.order_by(getattr(getattr(URL, col), sort_method)())
    num_urls = r.count()
    page = request.args.get("page", 1, type=int)
    r = r.paginate(page=page, per_page=_PAGE_NITEMS, error_out=False)

    # Generate rows
    rows = []
    for item in r.items:
        row = {col: getattr(item, col) for col in _COLS}

        ts = item.info_ts
        if ts is not None:
            row["last_update"] = ts.strftime("%Y-%m-%dT%H:%M:%S%z")
        else:
            row["last_update"] = None
        rows.append(row)

    return render_template(
        "overview.html",
        rows=rows,
        page=page,
        has_next=r.has_next,
        has_prev=r.has_prev,
        sort_by=sort_by,
        url_filter=url_filter,
        num_urls=num_urls,
    )
