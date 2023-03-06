# Module is for storing Pydantic models for communication between different components
# of the application.
from typing import Literal

from pydantic import BaseModel


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
