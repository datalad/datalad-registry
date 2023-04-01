# This file is for defining the API endpoints related to dataset URL metadata,
# i.e. the metadata of datasets at individual URLs.

from datalad_registry.com_models import URLMetadataModel
from datalad_registry.models import URLMetadata, db

from . import bp

_URL_PREFIX = "/url-metadata"


@bp.get(f"{_URL_PREFIX}/<int:url_metadata_id>")
def url_metadata(url_metadata_id):
    """
    Get URL metadata by ID.

    :param url_metadata_id: ID of the URL metadata to retrieve
    """
    data = URLMetadataModel.from_orm(db.get_or_404(URLMetadata, url_metadata_id))
    return data.dict()
