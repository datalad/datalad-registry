"""DataLad demo command"""

__docformat__ = "restructuredtext"

import logging
from typing import Optional

from datalad import cfg
from datalad.distribution.dataset import datasetmethod
from datalad.interface.base import Interface, build_doc, eval_results
from datalad.interface.results import get_status_dict
from datalad.support.constraints import EnsureNone, EnsureStr
from datalad.support.param import Parameter

from . import DEFAULT_BASE_ENDPOINT

lgr = logging.getLogger("datalad.registry.search")


# decoration auto-generates standard help
@build_doc
# all commands must be derived from Interface
class RegistrySearch(Interface):
    # first docstring line is used a short description in the cmdline help
    # the rest is put in the verbose help and manpage
    """Short description of the command

    Long description of arbitrary volume.
    """

    # parameters of the command, must be exhaustive
    _params_ = dict(
        # name of the parameter, must match argument name
        search_str=Parameter(
            # cmdline argument definitions, incl aliases
            args=("-s", "--search-str"),
            # documentation
            doc="""The search string used to perform a search identical to the one
            offered by the Web UI. Please consult the Web UI for the expected syntax of
            this search string by clicking on the "Show Search Query Syntax" button.""",
            # type checkers, constraint definition is automatically
            # added to the docstring
            constraints=EnsureStr(),
            required=True,
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
    # decorator binds the command to the Dataset class as a method
    @datasetmethod(name="registry_search")
    # generic handling of command results (logging, rendering, filtering, ...)
    @eval_results
    # signature must match parameter list above
    # additional generic arguments are added by decorators
    def __call__(search_str: str, base_endpoint: Optional[str] = None):
        # Set `base_endpoint` to the default if it is not provided.
        if base_endpoint is None:
            base_endpoint = cfg.get(
                "datalad_registry.base_endpoint", DEFAULT_BASE_ENDPOINT
            )

        # commands should be implemented as generators and should
        # report any results by yielding status dictionaries
        yield get_status_dict(
            # an action label must be defined, the command name make a good
            # default
            action="registry-search",
            # status labels are used to identify how a result will be reported
            # and can be used for filtering
            status="ok",
            # arbitrary result message, can be a str or tuple. in the latter
            # case string expansion with arguments is delayed until the
            # message actually needs to be rendered (analog to exception
            # messages)
            message=(
                "search_str: '%s'; base_endpoint: '%s'",
                search_str,
                base_endpoint,
            ),
        )

    @staticmethod
    def custom_result_renderer(res, **_kwargs):
        from datalad.ui import ui

        ui.message(res["message"][0] % res["message"][1:])
