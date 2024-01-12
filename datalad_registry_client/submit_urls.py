import logging
from typing import Any, Dict, Iterator, List, Optional

from datalad import cfg
from datalad.interface.base import Interface, build_doc, eval_results
from datalad.interface.results import get_status_dict
from datalad.support.constraints import EnsureNone, EnsureStr
from datalad.support.param import Parameter
import requests
from yarl import URL

from datalad_registry.blueprints.api import DATASET_URLS_PATH

from . import DEFAULT_BASE_ENDPOINT

lgr = logging.getLogger("datalad.registry.submit_urls")


@build_doc
class RegistrySubmitURLs(Interface):
    """Submit one or more URLs to a DataLad Registry instance."""

    _params_ = {
        "base_endpoint": Parameter(
            args=("--base-endpoint",),
            metavar="URL",
            doc=f"""The base API endpoint of the DataLad Registry instance to interact
            with. This defaults to the datalad_registry.base_endpoint option if set,
            or {DEFAULT_BASE_ENDPOINT} otherwise.""",
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
        urls: List[str], base_endpoint: Optional[str] = None
    ) -> Iterator[Dict[str, Any]]:
        if base_endpoint is None:
            base_endpoint = cfg.get(
                "datalad_registry.base_endpoint", DEFAULT_BASE_ENDPOINT
            )

        endpoint = URL(base_endpoint) / DATASET_URLS_PATH
        endpoint_str = str(endpoint)

        res_base = get_status_dict(
            action="registry-submit-urls",
            logger=lgr,
            base_endpoint=base_endpoint,
            endpoint=endpoint.human_repr(),
        )

        with requests.Session() as session:
            for url in urls:
                resp = session.post(endpoint_str, json={"url": url})

                res_base.update(URL=url)

                resp_status_code = resp.status_code
                if resp_status_code == 201:
                    yield get_status_dict(
                        **res_base,
                        status="ok",
                        message=("Registered %s", url),
                    )
                elif resp_status_code == 404:
                    yield get_status_dict(
                        **res_base,
                        status="error",
                        error_message=(
                            "Submitted URL: %s; " "Incorrect endpoint: %s",
                            url,
                            endpoint_str,
                        ),
                    )
                elif resp_status_code == 409:
                    yield get_status_dict(
                        **res_base,
                        status="error",
                        error_message=("The URL, %s, is already registered", url),
                    )
                elif resp_status_code == 422:
                    yield get_status_dict(
                        **res_base,
                        status="error",
                        error_message=(
                            "Submitted URL: %s; "
                            "Unprocessable argument(s) to server: %s",
                            url,
                            resp.text,
                        ),
                    )
                elif resp_status_code == 500:
                    yield get_status_dict(
                        **res_base,
                        status="error",
                        error_message=("Submitted URL: %s; " "Server Error", url),
                    )
                else:
                    yield get_status_dict(
                        **res_base,
                        status="error",
                        error_message=(
                            "Submitted URL: %s; "
                            "Server HTTP response code: %s; "
                            "Message from server: %s",
                            url,
                            resp_status_code,
                            resp.text,
                        ),
                    )
