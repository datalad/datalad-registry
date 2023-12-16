from flask import Response, current_app


def json_resp_from_str(json_str: str, **kwargs) -> Response:
    """
    Return a Flask response object, an object of the response class referenced by
    `Flask.response_class`, with the given JSON string as the response body

    :param json_str: The JSON string to use as the response body
    :return: The Flask response object with the given JSON string as the response body

    Note: This requires an active request or application context of Flask
    Note: Any extra keyword arguments are passed to the constructor
          of the response class except the `mimetype` keyword argument, which is
          fixed to `application/json`.
    """
    return current_app.response_class(json_str, mimetype="application/json", **kwargs)
