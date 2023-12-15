from functools import wraps
from http import HTTPStatus

from flask import Response, abort, current_app

from datalad_registry.conf import OperationMode


def json_resp_from_str(json_str: str, *args, **kwargs) -> Response:
    """
    Return a Flask response object, an object of the response class referenced by
    `Flask.response_class`, with the given JSON string as the response body

    :param json_str: The JSON string to use as the response body
    :return: The Flask response object with the given JSON string as the response body

    Note: This requires an active request or application context of Flask
    Note: Any extra position and keyword arguments are passed to the constructor
          of the response class except the `mimetype` keyword argument, which is
          fixed to `application/json`.
    """
    return current_app.response_class(
        json_str, *args, mimetype="application/json", **kwargs
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
