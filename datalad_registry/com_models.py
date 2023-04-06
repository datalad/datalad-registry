# Module is for storing Pydantic models for communication between different components
# of the application.
from typing import Literal

from pydantic import BaseModel, StrictStr


class MetadataRecord(BaseModel):
    dataset_version: StrictStr

    # Extractor and extraction parameters
    extractor_name: StrictStr
    extractor_version: StrictStr
    extraction_parameter: dict

    extracted_metadata: dict


class MetaExtractResult(BaseModel):
    action: Literal["meta_extract"]
    status: StrictStr
    metadata_record: MetadataRecord
