"""DataLad registry-get-urls command"""

__docformat__ = "restructuredtext"

import logging
from typing import Optional

from datalad import cfg
from datalad.interface.base import Interface, build_doc, eval_results
from datalad.interface.results import get_status_dict
from datalad.support.constraints import EnsureNone, EnsureStr
from datalad.support.param import Parameter
import requests
from yarl import URL

from datalad_registry.blueprints.api.dataset_urls import DatasetURLs

from . import DEFAULT_BASE_ENDPOINT

# The path of the dataset URLs resource on the DataLad Registry instance relative to
# the base API endpoint of the instance.
_DATASET_URLS_PATH = "dataset-urls"

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
            of the clone of the dataset of the URL in the local system,
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
        # Set `base_endpoint` to the default if it is not provided.
        if base_endpoint is None:
            base_endpoint = cfg.get(
                "datalad_registry.base_endpoint", DEFAULT_BASE_ENDPOINT
            )

        endpoint = URL(base_endpoint) / _DATASET_URLS_PATH

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
            target_url=target_url.human_repr(),
        )

        with requests.Session() as session:
            resp = session.get(str(target_url))

            resp_status_code = resp.status_code

            if resp_status_code == 200:
                dataset_urls = DatasetURLs.parse_raw(resp.text)

                yield get_status_dict(
                    status="ok",
                    message=f"{dataset_urls}",
                    **res_base,
                )
            elif resp_status_code == 404:
                yield get_status_dict(
                    status="error",
                    error_message=f"Incorrect target URL {target_url.human_repr()}",
                    **res_base,
                )
            elif resp_status_code == 422:
                yield get_status_dict(
                    status="error",
                    error_message="Unprocessable argument(s)",
                    **res_base,
                )
            elif resp_status_code == 500:
                yield get_status_dict(
                    status="error",
                    error_message="Server error",
                    **res_base,
                )
            else:
                yield get_status_dict(
                    status="error",
                    error_message=f"Server HTTP response code: {resp_status_code}; "
                    f"Message from server: {resp.text}",
                    **res_base,
                )
