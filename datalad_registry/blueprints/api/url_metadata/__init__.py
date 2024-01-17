# This file is for defining the API endpoints related to dataset URL metadata,
# i.e. the metadata of datasets at individual URLs.

from flask_openapi3 import APIBlueprint, Tag

from datalad_registry.models import URLMetadata, db

from .models import PathParams, URLMetadataModel
from .. import API_URL_PREFIX, COMMON_API_RESPONSES, URL_METADATA_PATH

bp = APIBlueprint(
    "url_metadata_api",
    __name__,
    url_prefix=f"{API_URL_PREFIX}/{URL_METADATA_PATH}",
    abp_tags=[Tag(name="URL Metadata", description="API endpoints for URL metadata")],
    abp_responses=COMMON_API_RESPONSES,
)


@bp.get("/<int:url_metadata_id>", responses={"200": URLMetadataModel})
def url_metadata(path: PathParams):
    """
    Get URL metadata by ID.
    """
    data = URLMetadataModel.from_orm(db.get_or_404(URLMetadata, path.url_metadata_id))
    return data.dict()
