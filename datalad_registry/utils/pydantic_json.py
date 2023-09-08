# This module extends the JSON serializer used by Celery
# by adding support for Pydantic models.
# This serializer should be used together with the @validate_arguments decorator
# from Pydantic to allow Pydantic models to be passed to Celery tasks as arguments.

from kombu.utils.json import dumps, loads
from pydantic.json import pydantic_encoder


def pydantic_dumps(obj):
    return dumps(obj, default=pydantic_encoder)


pydantic_loads = loads
