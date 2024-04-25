from functools import wraps
from http import HTTPStatus

from flask import current_app, request

from datalad_registry.conf import OperationMode
from datalad_registry.utils.flask_tools import json_resp_from_str

from . import HTTPExceptionResp


def disable_in_read_only_mode(view_func):
    """
    Decorator for view functions that should be disabled in read-only mode

    :param view_func: The view function to decorate
    :return: The decorated view function
    """

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if (
            current_app.config["DATALAD_REGISTRY_OPERATION_MODE"]
            is OperationMode.READ_ONLY
        ):

            resp_status = HTTPStatus.METHOD_NOT_ALLOWED

            # Construct the response body
            resp_body = HTTPExceptionResp(
                code=resp_status,
                name=resp_status.phrase,
                description="This method on the requested resource is not available "
                "through a read-only server.",
            )

            # Get remaining supported methods on the endpoint, representing a resource,
            # to construct the required `Allow` header for a 405, Method Not Allowed,
            # response
            remaining_supported_methods: set[str] = set()
            for rule in current_app.url_map.iter_rules():
                if (
                    str(rule) == str(request.url_rule)
                    and rule.endpoint != request.endpoint
                ):
                    # `rule` is of the current requested path
                    # but not of the current endpoint
                    remaining_supported_methods.update(rule.methods)

            return json_resp_from_str(
                resp_body.json(exclude_none=True),
                status=resp_status,
                headers={"Allow": ", ".join(remaining_supported_methods)},
            )

        else:
            return view_func(*args, **kwargs)

    return wrapper
