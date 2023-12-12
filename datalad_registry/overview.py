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

    select_stmt = select(RepoUrl)

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
            select_stmt = select_stmt.filter(criteria)

    # Sort
    select_stmt = select_stmt.group_by(RepoUrl)
    sort_by = request.args.get("sort", default_sort_scheme, type=str)
    if sort_by not in _SORT_ATTRS:
        lgr.debug("Ignoring unknown sort parameter: %s", sort_by)
        sort_by = default_sort_scheme
    col, sort_method = _SORT_ATTRS[sort_by]
    select_stmt = select_stmt.order_by(
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
                m = mr.extracted_metadata
                m['type'] = 'dataset'
                m['dataset_id'] = repo_url_row.ds_id
                # Didn't want to translate yet
                # metadatas[mr.extractor_name] = dl.catalog_translate(m)
                # TEMP: get it without translation
                metadatas[mr.extractor_name] = m
            lgr.warning(f"ROW: {metadatas}")
    # TODO: figure out how to pass all the metadata goodness to the catalog
    return send_from_directory('/app-catalog', path)
