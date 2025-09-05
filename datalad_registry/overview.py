"""Blueprint for /overview table view
"""

import logging

from flask import Blueprint, render_template, request
from humanize import intcomma
from sqlalchemy import nullslast, select

from datalad_registry.blueprints.api.dataset_urls.tools import get_collection_stats
from datalad_registry.models import RepoUrl, db
from datalad_registry.search import parse_query

lgr = logging.getLogger(__name__)
bp = Blueprint("overview", __name__, url_prefix="/overview")

# _SORT_ATTRS removed - now using _AVAILABLE_COLUMNS with db_field mapping

# Available columns with their metadata
_AVAILABLE_COLUMNS = {
    "url": {"label": "URL", "sortable": True, "db_field": "url"},
    "dataset": {"label": "Dataset", "sortable": False},
    "commit": {"label": "Commit", "sortable": False},
    "head_dt": {"label": "Last commit date", "sortable": True, "db_field": "head_dt"},
    "keys": {
        "label": "Annex keys",
        "sortable": True,
        "tooltip": "Number of annex keys",
        "db_field": "annex_key_count",
    },
    "annexed_files_count": {
        "label": "Nr of Annexed files",
        "sortable": True,
        "tooltip": "Number of annexed files in working tree",
        "db_field": "annexed_files_in_wt_count",
    },
    "annexed_files_size": {
        "label": "Size of Annexed files",
        "sortable": True,
        "tooltip": "Size of annexed files in working tree",
        "db_field": "annexed_files_in_wt_size",
    },
    "update": {"label": "Last update", "sortable": True, "db_field": "last_update_dt"},
    "git_objects": {
        "label": "Size of .git/objects",
        "sortable": True,
        "db_field": "git_objects_kb",
    },
    "metadata": {"label": "Metadata", "sortable": False},
}

# Default columns to display
_DEFAULT_COLUMNS = [
    "url",
    "dataset",
    "commit",
    "head_dt",
    "keys",
    "annexed_files_count",
    "annexed_files_size",
    "update",
    "git_objects",
    "metadata",
]


# Register humanize.intcomma as a Jinja2 filter
bp.add_app_template_filter(intcomma, "intcomma")


@bp.get("/")
def overview():  # No type hints due to mypy#7187.
    default_sort_column = "update"
    default_sort_direction = "desc"

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

    # Handle configurable columns
    columns_param = request.args.get("columns", None, type=str)
    if columns_param:
        # Parse comma-separated column names
        requested_columns = [col.strip() for col in columns_param.split(",")]
        # Filter out invalid column names
        visible_columns = [
            col for col in requested_columns if col in _AVAILABLE_COLUMNS
        ]
        if not visible_columns:
            visible_columns = _DEFAULT_COLUMNS
    else:
        visible_columns = _DEFAULT_COLUMNS

    # Handle sorting using new system
    sort_by_param = request.args.get("sort_by", default_sort_column, type=str)
    sort_direction = request.args.get("sort", default_sort_direction, type=str)
    # Validate sort_by parameter
    if sort_by_param in _AVAILABLE_COLUMNS and _AVAILABLE_COLUMNS[sort_by_param].get(
        "sortable"
    ):
        col = _AVAILABLE_COLUMNS[sort_by_param]["db_field"]
        sort_method = sort_direction if sort_direction in ["asc", "desc"] else "asc"
    else:
        lgr.debug("Ignoring unknown sort_by parameter: %s", sort_by_param)
        sort_by_param = default_sort_column
        col = _AVAILABLE_COLUMNS[default_sort_column]["db_field"]
        sort_method = default_sort_direction

    # Apply sorting
    select_stmt = base_select_stmt.order_by(
        nullslast(getattr(getattr(RepoUrl, col), sort_method)())
    )

    # Paginate
    pagination = db.paginate(select_stmt)

    # Gather stats of the returned collection of datasets
    stats = get_collection_stats(base_select_stmt)

    return render_template(
        "overview.html",
        pagination=pagination,
        stats=stats,
        sort_by_param=sort_by_param,
        sort_direction=sort_method,  # Use the validated sort_method
        search_query=query,
        search_error=search_error,
        visible_columns=visible_columns,
        available_columns=_AVAILABLE_COLUMNS,
        columns_param=columns_param,
    )
