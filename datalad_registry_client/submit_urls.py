import logging
from typing import Any, Dict, Iterator, List, Optional

from datalad import cfg
from datalad.interface.base import Interface, build_doc, eval_results
from datalad.interface.results import get_status_dict
from datalad.support.constraints import EnsureNone, EnsureStr
from datalad.support.param import Parameter
import requests

from datalad_registry.utils.url_encoder import url_encode
from datalad_registry_client.consts import DEFAULT_ENDPOINT

lgr = logging.getLogger("datalad.registry.submit_urls")


@build_doc
class RegistrySubmitURLs(Interface):
    """Submit one or more URLs to a DataLad Registry instance."""

    _params_ = {
        "endpoint": Parameter(
            args=("--endpoint",),
            metavar="URL",
            doc=f"""DataLad Registry instance to use (no trailing slash).
            This defaults to the datalad_registry.endpoint option, if set,
            or {DEFAULT_ENDPOINT} otherwise.""",
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
            endpoint = cfg.get("datalad_registry.endpoint", DEFAULT_ENDPOINT)
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
                        "url_encoded": url_encoded,
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
                        "url_encoded": url_encoded,
                        "status": "error",
                        "message": ("Submitting URL failed: %s", exc),
                    }
                    continue
                yield {
                    **res_base,
                    "url": url,
                    "url_encoded": url_encoded,
                    "status": "ok",
                    "message": ("%s: %s", msg, url),
                }
