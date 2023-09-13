"""Blueprint for /overview table view
"""

import logging

from flask import Blueprint, render_template, request
from sqlalchemy import Text, nullslast, or_

from datalad_registry.models import RepoUrl, URLMetadata, db

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

    r = db.session.query(RepoUrl)

    # Apply filter if provided
    filter = request.args.get("filter", None, type=str)
    if filter:
        lgr.debug("Filter URLs by '%s'", filter)

        escape = "\\"
        escaped_filter = (
            filter.replace(escape, escape + escape)
            .replace("%", escape + "%")
            .replace("_", escape + "_")
        )
        pattern = f"%{escaped_filter}%"

        r = r.filter(
            or_(
                RepoUrl.url.ilike(pattern, escape=escape),
                RepoUrl.ds_id.ilike(pattern, escape=escape),
                RepoUrl.head.ilike(pattern, escape=escape),
                RepoUrl.head_describe.ilike(pattern, escape=escape),
                RepoUrl.branches.ilike(pattern, escape=escape),
                RepoUrl.tags.ilike(pattern, escape=escape),
                RepoUrl.metadata_.any(
                    or_(
                        URLMetadata.extractor_name.ilike(pattern, escape=escape),
                        # search the entire JSON column as text
                        URLMetadata.extracted_metadata.cast(Text).ilike(
                            pattern, escape=escape
                        ),
                    )
                ),
            )
        )

    # Sort
    r = r.group_by(RepoUrl)
    sort_by = request.args.get("sort", default_sort_scheme, type=str)
    if sort_by not in _SORT_ATTRS:
        lgr.debug("Ignoring unknown sort parameter: %s", sort_by)
        sort_by = default_sort_scheme
    col, sort_method = _SORT_ATTRS[sort_by]
    r = r.order_by(nullslast(getattr(getattr(RepoUrl, col), sort_method)()))

    # Paginate
    pagination = r.paginate()

    return render_template(
        "overview.html",
        pagination=pagination,
        sort_by=sort_by,
        url_filter=filter,
    )
