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


@bp.route("/")
def overview():
    if request.method == "GET":
        r = db.session.query(URL).group_by(URL.ds_id)
        r = r.order_by(URL.info_ts.desc())
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
            num_urls=num_urls)
