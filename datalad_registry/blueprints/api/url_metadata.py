# This file is for defining the API endpoints related to dataset URL metadata,
# i.e. the metadata of datasets at individual URLs.

from flask_openapi3 import Tag
from pydantic import BaseModel, Field, StrictStr

from datalad_registry.models import URLMetadata, db

from . import bp

_URL_PREFIX = "/url-metadata"
_TAG = Tag(name="URL Metadata", description="API endpoints for URL metadata")


class _PathParams(BaseModel):
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


@bp.get(
    f"{_URL_PREFIX}/<int:url_metadata_id>",
    responses={"200": URLMetadataModel},
    tags=[_TAG],
)
def url_metadata(path: _PathParams):
    """
    Get URL metadata by ID.
    """
    data = URLMetadataModel.from_orm(db.get_or_404(URLMetadata, path.url_metadata_id))
    return data.dict()
