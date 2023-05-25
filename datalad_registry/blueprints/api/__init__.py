from pydantic import BaseModel, Field

API_URL_PREFIX = "/api/v2"


class HTTPExceptionResp(BaseModel):
    """
    Default HTTP exception response
    """

    code: int = Field(..., description="HTTP status code")
    name: str = Field(..., description="HTTP status name")
    description: str = Field(..., description="HTTP status description")


# The responses common to all API endpoints
COMMON_API_RESPONSES = {"404": HTTPExceptionResp, "500": HTTPExceptionResp}
