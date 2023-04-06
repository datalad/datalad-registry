# This file is for defining the API endpoints related to dataset URls

from datetime import datetime
from pathlib import Path
from typing import Optional, Union
from uuid import UUID

from flask_openapi3 import Tag
from pydantic import AnyUrl, BaseModel, Field, FileUrl

from datalad_registry.models import URL, db
from datalad_registry.utils.flask_tools import json_resp_from_str

from . import bp

_URL_PREFIX = "/dataset-urls"
_TAG = Tag(name="Dataset URLs", description="API endpoints for dataset URLs")


class _PathParams(BaseModel):
    """
    Pydantic model for representing the path parameters for API endpoints related to
    dataset URLs.
    """

    id: int = Field(..., description="The ID of the dataset URL")


class DatasetURLModel(BaseModel):
    """
    Model for representing the database model URL for communication
    """

    id: int = Field(..., alias="id", description="The ID of the dataset URL")
    url: Union[FileUrl, AnyUrl, Path] = Field(..., description="The URL")
    dataset_id: Optional[UUID] = Field(
        ..., alias="ds_id", description="The ID, a UUID, of the dataset"
    )
    describe: Optional[str] = Field(
        ...,
        alias="head_describe",
        description="The output of `git describe --tags --always` on the dataset",
    )
    annex_key_count: Optional[int] = Field(..., description="The number of annex keys ")
    annexed_files_in_wt_count: Optional[int] = Field(
        ..., description="The number of annexed files in the working tree"
    )
    annexed_files_in_wt_size: Optional[int] = Field(
        ..., description="The size of annexed files in the working tree in bytes"
    )
    last_update: Optional[datetime] = Field(
        ...,
        alias="info_ts",
        description="The last time the local copy of the dataset was updated",
    )
    git_objects_kb: Optional[int] = Field(
        ..., description="The size of the `.git/objects` in KiB"
    )

    class Config:
        orm_mode = True


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


@bp.get(
    f"{_URL_PREFIX}/<int:id>",
    responses={"200": DatasetURLModel},
    tags=[_TAG],
)
def dataset_url(path: _PathParams):
    """
    Get a dataset URL by ID.
    """
    ds_url = DatasetURLModel.from_orm(db.get_or_404(URL, path.id))
    return json_resp_from_str(ds_url.json())
