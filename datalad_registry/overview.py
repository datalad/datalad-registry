"""Blueprint for /overview table view
"""

import logging
import time

from flask import Blueprint
from flask import render_template
from flask import request

from datalad_registry.models import db
from datalad_registry.models import URL

lgr = logging.getLogger(__name__)
bp = Blueprint("overview", __name__, url_prefix="/overview")

_PAGE_NITEMS = 25  # TODO: Should eventually be configurable by app.
_SORT_ATTRS = {"keys-asc": ("annex_key_count", "asc"),
               "keys-desc": ("annex_key_count", "desc"),
               "update-asc": ("info_ts", "asc"),
               "update-desc": ("info_ts", "desc"),
               "url-asc": ("url", "asc"),
               "url-desc": ("url", "desc")}


@bp.route("/")
def overview():  # No type hints due to mypy#7187.
    if request.method == "GET":
        r = db.session.query(URL)
        url_filter = request.args.get('filter', None, type=str)
        if url_filter:
            lgr.debug("Filter URLs by '%s'", url_filter)
            r = r.filter(URL.url.contains(url_filter, autoescape=True))

        r = r.group_by(URL.ds_id)
        sort_by = request.args.get('sort', "update-desc", type=str)
        if sort_by not in _SORT_ATTRS:
            lgr.debug("Ignoring unknown sort parameter: %s", sort_by)
            sort_by = "update-desc"
        col, sort_method = _SORT_ATTRS[sort_by]

        r = r.order_by(getattr(getattr(URL, col), sort_method)())
        num_urls = r.count()
        page = request.args.get('page', 1, type=int)
        r = r.paginate(page, _PAGE_NITEMS, False)
        rows = []
        for info in r.items:
            row = {}
            for col in ["ds_id", "url", "annex_key_count", "head",
                        "head_describe"]:
                row[col] = getattr(info, col)

            ts = info.info_ts
            if ts:
                row["last_update"] = time.strftime('%Y-%m-%dT%H:%M%z',
                                                   time.gmtime(ts))
            else:
                row["last_update"] = None
            rows.append(row)
        return render_template(
            'overview.html', rows=rows,
            page=page, has_next=r.has_next, has_prev=r.has_prev,
            sort_by=sort_by, url_filter=url_filter,
            num_urls=num_urls)
