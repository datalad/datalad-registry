"""DataLad registry-get-urls command"""

__docformat__ = "restructuredtext"

import logging
from typing import Optional

from datalad.interface.base import Interface, build_doc, eval_results
from datalad.interface.results import get_status_dict
from datalad.support.constraints import EnsureNone, EnsureStr
from datalad.support.param import Parameter
import requests
from yarl import URL

from datalad_registry.blueprints.api import DATASET_URLS_PATH

from . import DEFAULT_BASE_ENDPOINT
from .utils import get_base_endpoint

lgr = logging.getLogger("datalad.registry.get_urls")


# decoration auto-generates standard help
@build_doc
# all commands must be derived from Interface
class RegistryGetURLs(Interface):
    # first docstring line is used a short description in the cmdline help
    # the rest is put in the verbose help and manpage
    """Fetch dataset URLs

    Fetch the dataset URLs from a Datalad registry instance that meets the constraints
    specified by the provided options.
    """

    # parameters of the command, must be exhaustive
    _params_ = dict(
        # name of the parameter, must match argument name
        cache_path=Parameter(
            # cmdline argument definitions, incl aliases
            args=("-c", "--cache-path"),
            # documentation
            doc="""The full or relative path (relating to the base cache path),
            of the clone of the dataset at the URL in the local system,
            the system running the Celery worker. If a full path is provided,
            only the last three components are used in the query.""",
            # type checkers, constraint definition is automatically
            # added to the docstring
            constraints=EnsureStr() | EnsureNone(),
        ),
        base_endpoint=Parameter(
            args=("-e", "--base-endpoint"),
            doc=f"""The base API endpoint of the DataLad Registry instance to interact
            with. This defaults to the datalad_registry.base_endpoint option if set,
            or {DEFAULT_BASE_ENDPOINT} otherwise.""",
            constraints=EnsureStr() | EnsureNone(),
        ),
    )

    @staticmethod
    # generic handling of command results (logging, rendering, filtering, ...)
    @eval_results
    # signature must match parameter list above
    # additional generic arguments are added by decorators
    def __call__(cache_path: Optional[str] = None, base_endpoint: Optional[str] = None):
        from datalad_registry.blueprints.api.dataset_urls.models import DatasetURLPage

        # Set `base_endpoint` based on configuration if it is not provided.
        if base_endpoint is None:
            base_endpoint = get_base_endpoint()

        endpoint = URL(base_endpoint) / DATASET_URLS_PATH

        target_url = (
            endpoint.with_query(cache_path=cache_path)
            if cache_path is not None
            else endpoint
        )

        res_base = get_status_dict(
            # an action label must be defined, the command name make a good default
            action="registry-get-urls",
            logger=lgr,
            base_endpoint=base_endpoint,
            endpoint=endpoint.human_repr(),
        )

        ds_urls: list[str] = []  # For storing returned dataset URLs from the server
        with requests.Session() as session:
            while True:
                resp = session.get(str(target_url))

                resp_status_code = resp.status_code

                if resp_status_code == 200:
                    ds_url_pg = DatasetURLPage.parse_raw(resp.text)
                    ds_urls.extend(str(i.url) for i in ds_url_pg.dataset_urls)

                    if ds_url_pg.next_pg is None:
                        # No more page to fetch

                        yield get_status_dict(
                            status="ok",
                            message=str(ds_urls),
                            **res_base,
                        )
                        break
                    else:
                        # More pages to fetch

                        target_url = target_url.join(URL(ds_url_pg.next_pg))

                elif resp_status_code == 404:
                    yield get_status_dict(
                        status="error",
                        error_message=f"Incorrect target URL {target_url.human_repr()}",
                        **res_base,
                    )
                    break
                elif resp_status_code == 422:
                    yield get_status_dict(
                        status="error",
                        error_message="Unprocessable argument(s)",
                        **res_base,
                    )
                    break
                elif resp_status_code == 500:
                    yield get_status_dict(
                        status="error",
                        error_message="Server error",
                        **res_base,
                    )
                    break
                else:
                    yield get_status_dict(
                        status="error",
                        error_message=f"Server HTTP response code: {resp_status_code}; "
                        f"Message from server: {resp.text}",
                        **res_base,
                    )
                    break
