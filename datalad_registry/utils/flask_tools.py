from functools import wraps
from http import HTTPStatus
from typing import Optional, Union

from flask import abort, current_app

from datalad_registry.conf import OperationMode


def json_resp_from_str(
    json_str: str, status: Optional[Union[int, str, HTTPStatus]] = None
):
    """
    Return a Flask response object with the given JSON string as the response body

    :param json_str: The JSON string to use as the response body
    :param status: The HTTP response status code of the response
    :return: The Flask response object with the given JSON string as the response body

    Note: This requires an active request or application context of Flask
    """
    return current_app.response_class(
        json_str, mimetype="application/json", status=status
    )


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
            abort(
                HTTPStatus.IM_A_TEAPOT,
                description="This operation is not available from a read-only server.",
            )
        else:
            return view_func(*args, **kwargs)

    return wrapper
