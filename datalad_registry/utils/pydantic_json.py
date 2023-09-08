# This module extends the default JSON serializer used by Celery by adding JSON
# serialization support for types supported by Pydantic for JSON serialization.
# These are the types that are allowed as a type for a field in a Pydantic model.
# They include `datetime.datetime`, `decimal.Decimal`, `pathlib.Path`, `uuid.UUID`,
# Pydantic models themselves, and more.
# This serializer should be used in conjunction with the @validate_arguments decorator
# from Pydantic to allow the additional types to be passed to Celery tasks as arguments.

from kombu.utils.json import dumps, loads
from pydantic.json import pydantic_encoder


def pydantic_dumps(obj):
    return dumps(obj, default=pydantic_encoder)


pydantic_loads = loads
