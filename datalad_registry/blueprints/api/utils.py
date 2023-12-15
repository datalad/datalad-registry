from functools import wraps
from http import HTTPStatus

from flask import abort, current_app

from datalad_registry import OperationMode


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
