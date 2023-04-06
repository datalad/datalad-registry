from http import HTTPStatus
from typing import Optional, Union

from flask import current_app


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
