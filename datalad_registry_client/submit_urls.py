import logging
from typing import Any
from typing import Dict
from typing import Optional
from typing import Iterator
from typing import List

import requests
from datalad import cfg
from datalad.distribution.dataset import Dataset
from datalad.interface.base import build_doc
from datalad.interface.base import Interface
from datalad.interface.results import get_status_dict
from datalad.interface.utils import eval_results
from datalad.support.constraints import EnsureNone
from datalad.support.constraints import EnsureStr
from datalad.support.param import Parameter

from datalad_registry.utils import url_encode

lgr = logging.getLogger("datalad.registry.submit_urls")


@build_doc
class RegistrySubmitURLs(Interface):
    """Submit one or more URLs to a DataLad Registry instance."""

    _params_ = {
        "endpoint": Parameter(
            args=("--endpoint",),
            metavar="URL",
            doc="""DataLad Registry instance to use (no trailing slash).
            This defaults to the datalad_registry.endpoint option, if set,
            or http://127.0.0.1:5000/v1 otherwise.""",
            constraints=EnsureStr() | EnsureNone(),
        ),
        "urls": Parameter(
            args=("urls",),
            metavar="URL",
            doc="""URLs to register""",
            nargs="+",
            constraints=EnsureStr() | EnsureNone(),
        ),
    }

    @staticmethod
    @eval_results
    def __call__(
        urls: List[str], endpoint: Optional[str] = None
    ) -> Iterator[Dict[str, Any]]:
        if endpoint is None:
            endpoint = cfg.get("datalad_registry.endpoint", "http://127.0.0.1:5000/v1")
        res_base = get_status_dict(
            action="registry-submit-urls",
            logger=lgr,
            endpoint=endpoint,
        )
        with requests.Session() as s:
            for url in urls:
                url_encoded = url_encode(url)
                try:
                    r = s.get(f"{endpoint}/urls/{url_encoded}", timeout=1)
                    r.raise_for_status()
                except requests.exceptions.RequestException as exc:
                    yield {
                        **res_base,
                        "url": url,
                        "status": "error",
                        "message": ("Check if URL is known failed: %s", exc),
                    }
                    continue
                url_info = r.json()
                if url_info.get("status") == "unknown":
                    msg = "Registered URL"
                else:
                    msg = "Announced update"
                try:
                    r = s.patch(f"{endpoint}/urls/{url_encoded}", timeout=1)
                    r.raise_for_status()
                except requests.exceptions.RequestException as exc:
                    yield {
                        **res_base,
                        "url": url,
                        "status": "error",
                        "message": ("Submitting URL failed: %s", exc),
                    }
                    continue
                yield {
                    **res_base,
                    "url": url,
                    "status": "ok",
                    "message": ("%s: %s", msg, url),
                }
