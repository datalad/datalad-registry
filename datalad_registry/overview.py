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
                RepoUrl.branches.cast(Text).ilike(pattern, escape=escape),
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

import json
from flask import send_from_directory
import datalad.api as dl


# @bp.route('/catalog/', defaults={'path': ''})
# TODO: move from placing dataset identifier within path -- place into query
# TODO: do not use ID may be but use URL, or allow for both -- that would make it possible to make those URLs
#  pointing to datasets easier to create/digest for humans
@bp.route('/catalog/<int:id_>/<path:path>')
def send_report(id_, path):
    # ds_id = request.args.get("id", None, type=int)
    if not path:
        path = "index.html"
    if path == "index.html":
        lgr.warning(f"PATH: {path}  id: {id_}")
        # let's get metadata for the ds_id
        repo_url_row = db.session.execute(
            db.select(RepoUrl).filter_by(id=id_)
        ).one_or_none()
        if repo_url_row:
            repo_url_row = repo_url_row[0]
            metadatas = {}
            for mr in repo_url_row.metadata_:
                if mr.extractor_name not in {'metalad_core', 'bids_dataset', 'metalad_studyminimeta'}:
                    continue
                # TODO: here metadta record had only @context and @graph and no other fields
                # figure out if enough....
                m = mr.extracted_metadata
                m['type'] = 'dataset'
                m['dataset_id'] = repo_url_row.ds_id
                # Didn't want to translate yet
                lgr.warning(f"Translating record with keys {m.keys()}")
                metadatas[mr.extractor_name] = dl.catalog_translate(m)
                # metadatas[mr.extractor_name] = m
            lgr.warning(f"ROW: {metadatas}")
    # TODO: figure out how to pass all the metadata goodness to the catalog
    return send_from_directory('/app-catalog', path)
