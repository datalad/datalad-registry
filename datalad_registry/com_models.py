# Module is for storing Pydantic models for communication between different components
# of the application.
from typing import Literal

from pydantic import BaseModel, StrictStr


class MetadataRecord(BaseModel):
    dataset_version: str

    # Extractor and extraction parameters
    extractor_name: str
    extractor_version: str
    extraction_parameter: dict

    extracted_metadata: dict


class MetaExtractResult(BaseModel):
    action: Literal["meta_extract"]
    status: str
    metadata_record: MetadataRecord


class URLMetadataModel(BaseModel):
    """
    Pydantic model for representing the database model URLMetadata for communication
    in JSON
    """

    dataset_describe: StrictStr
    dataset_version: StrictStr
    extractor_name: StrictStr
    extractor_version: StrictStr
    extraction_parameter: dict
    extracted_metadata: dict

    class Config:
        orm_mode = True
