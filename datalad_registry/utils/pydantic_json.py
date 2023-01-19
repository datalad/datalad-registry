# This module extends the JSON serializer used by Celery
# by adding support for Pydantic models.
# This serializer should be used together with the @validate_arguments decorator
# from Pydantic to allow Pydantic models to be passed to Celery tasks as arguments.

from kombu.utils.json import JSONEncoder, dumps, loads
from pydantic import BaseModel


class PydanticModelJSONEncoder(JSONEncoder):
    def default(self, obj, *args, **kwargs):
        if isinstance(obj, BaseModel):
            return obj.dict()
        return JSONEncoder.default(self, obj, *args, **kwargs)


def pydantic_model_dumps(obj):
    return dumps(obj, cls=PydanticModelJSONEncoder)


pydantic_model_loads = loads
