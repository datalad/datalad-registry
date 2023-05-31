from pydantic import BaseModel, Field, StrictStr


class PathParams(BaseModel):
    """
    Pydantic model for representing the path parameters for the URL metadata API
    endpoints.
    """

    url_metadata_id: int = Field(..., description="The ID of the URL metadata")


class URLMetadataModel(BaseModel):
    """
    Model for representing the database model URLMetadata for communication
    """

    dataset_describe: StrictStr
    dataset_version: StrictStr
    extractor_name: StrictStr
    extractor_version: StrictStr
    extraction_parameter: dict
    extracted_metadata: dict

    class Config:
        orm_mode = True


class URLMetadataRef(BaseModel):
    """
    Model for referencing metadata of a dataset at a URL extracted by an extractor
    through the API
    """

    extractor_name: StrictStr
    link: StrictStr  # This link is relative
