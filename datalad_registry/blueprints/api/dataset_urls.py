# This file is for defining the API endpoints related to dataset URls

from . import bp

_URL_PREFIX = "/dataset-urls"


@bp.post(f"{_URL_PREFIX}")
def create_dataset_url():
    """
    Create a new dataset URL.
    """
    raise NotImplementedError


@bp.get(f"{_URL_PREFIX}")
def dataset_urls():
    """
    Get all dataset URLs that satisfy the constraints imposed by the query parameters.
    """
    raise NotImplementedError


@bp.get(f"{_URL_PREFIX}/<int:dataset_url_id>")
def dataset_url(dataset_url_id):
    """
    Get a dataset URL by ID.
    """
    raise NotImplementedError
