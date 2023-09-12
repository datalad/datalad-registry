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
        r = r.filter(
            or_(
                RepoUrl.url.contains(filter, autoescape=True),
                RepoUrl.ds_id.contains(filter, autoescape=True),
                RepoUrl.head.contains(filter, autoescape=True),
                RepoUrl.head_describe.contains(filter, autoescape=True),
                RepoUrl.branches.contains(filter, autoescape=True),
                RepoUrl.tags.contains(filter, autoescape=True),
                RepoUrl.metadata_.any(
                    or_(
                        URLMetadata.extractor_name.contains(filter, autoescape=True),
                        # for a specific field: .as_string()
                        # URLMetadata.extracted_metadata['dataset_version'].as_string().contains(filter)
                        # It seems to serialize nested fields
                        # URLMetadata.extracted_metadata['entities'].as_string().contains(filter)
                        # search the entire record!
                        URLMetadata.extracted_metadata.cast(Text).contains(
                            filter, autoescape=True
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
