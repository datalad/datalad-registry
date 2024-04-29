from typing import Any

from pydantic import BaseModel, Field, StrictStr


class PathParams(BaseModel):
    """
    Pydantic model for representing the path parameters for the URL metadata API
    endpoints.
    """

    url_metadata_id: int = Field(..., description="The ID of the URL metadata")


class _URLMetadataRep(BaseModel):
    """
    Base model for representing metadata of a dataset at a URL
    """

    extractor_name: StrictStr


class URLMetadataModel(_URLMetadataRep):
    """
    Model for representing the database model URLMetadata for communication
    """

    dataset_describe: StrictStr
    dataset_version: StrictStr
    extractor_version: StrictStr
    extraction_parameter: dict
    extracted_metadata: Any

    class Config:
        orm_mode = True


class URLMetadataRef(_URLMetadataRep):
    """
    Model for referencing metadata of a dataset at a URL extracted by an extractor
    through the API
    """

    link: StrictStr
