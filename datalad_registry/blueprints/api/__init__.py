from pydantic import BaseModel, Field

API_URL_PREFIX = "/api/v2"

# The path of the dataset URL resources on the DataLad Registry instance relative to
# the base API endpoint of the instance.
DATASET_URLS_PATH = "dataset-urls"

# The path of the URL metadata resources on the DataLad Registry instance relative to
# the base API endpoint of the instance.
URL_METADATA_PATH = "url-metadata"


class HTTPExceptionResp(BaseModel):
    """
    Default HTTP exception response
    """

    code: int = Field(..., description="HTTP status code")
    name: str = Field(..., description="HTTP status name")
    description: str = Field(..., description="HTTP status description")


# The responses common to all API endpoints
COMMON_API_RESPONSES = {"404": HTTPExceptionResp, "500": HTTPExceptionResp}
