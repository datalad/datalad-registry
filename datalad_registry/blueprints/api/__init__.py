from flask_openapi3 import APIBlueprint
from pydantic import BaseModel, Field


class HTTPExceptionResp(BaseModel):
    """
    Default HTTP exception response
    """

    code: int = Field(..., description="HTTP status code")
    name: str = Field(..., description="HTTP status name")
    description: str = Field(..., description="HTTP status description")


bp = APIBlueprint(
    "api",
    __name__,
    url_prefix="/api/v2",
    abp_responses={
        "404": HTTPExceptionResp,
        "500": HTTPExceptionResp,
    },
)

# Ignoring flake8 rules in the following import.
# F401: imported but unused
# E402: module level import not at top of file
# Attach dataset URL related API endpoints
# Attach URL metadata related API endpoints
from . import dataset_urls  # noqa: F401, E402
from . import url_metadata  # noqa: F401, E402
