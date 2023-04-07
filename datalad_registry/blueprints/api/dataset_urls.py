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


class _QueryParams(BaseModel):
    """
    Pydantic model for representing the query parameters to query
    the dataset_urls endpoint
    """

    url: Optional[Union[FileUrl, AnyUrl, Path]] = Field(None, description="The URL")

    dataset_id: Optional[UUID] = Field(
        None, description="The ID, a UUID, of the dataset"
    )

    min_annex_key_count: Optional[int] = Field(
        None, description="The minimum number of annex keys "
    )
    max_annex_key_count: Optional[int] = Field(
        None, description="The maximum number of annex keys "
    )

    min_annexed_files_in_wt_count: Optional[int] = Field(
        None, description="The minimum number of annexed files in the working tree"
    )
    max_annexed_files_in_wt_count: Optional[int] = Field(
        None, description="The maximum number of annexed files in the working tree"
    )

    min_annexed_files_in_wt_size: Optional[int] = Field(
        None,
        description="The minimum size of annexed files in the working tree in bytes",
    )
    max_annexed_files_in_wt_size: Optional[int] = Field(
        None,
        description="The maximum size of annexed files in the working tree in bytes",
    )

    earliest_last_update: Optional[datetime] = Field(
        None,
        description="The earliest last update time",
    )
    latest_last_update: Optional[datetime] = Field(
        None,
        description="The latest last update time",
    )

    min_git_objects_kb: Optional[int] = Field(
        None, description="The minimum size of the `.git/objects` in KiB"
    )
    max_git_objects_kb: Optional[int] = Field(
        None, description="The maximum size of the `.git/objects` in KiB"
    )


class DatasetURLSubmitModel(BaseModel):
    """
    Model for representing the database model URL for submission communication
    """

    url: Union[FileUrl, AnyUrl, Path] = Field(..., description="The URL")


class DatasetURLRespModel(DatasetURLSubmitModel):
    """
    Model for representing the database model URL in response communication
    """

    id: int = Field(..., alias="id", description="The ID of the dataset URL")
    dataset_id: Optional[UUID] = Field(
        ..., alias="ds_id", description="The ID, a UUID, of the dataset"
    )
    describe: Optional[str] = Field(
        ...,
        alias="head_describe",
        description="The output of `git describe --tags --always` on the dataset",
    )
    annex_key_count: Optional[int] = Field(..., description="The number of annex keys")
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


class DatasetURLs(BaseModel):
    """
    Model for representing a list of dataset URLs in response communication
    """

    __root__: list[DatasetURLRespModel]

    class Config:
        orm_mode = True


@bp.post(f"{_URL_PREFIX}")
def create_dataset_url():
    """
    Create a new dataset URL.
    """
    raise NotImplementedError


@bp.get(
    f"{_URL_PREFIX}",
    responses={"200": DatasetURLs},
    tags=[_TAG],
)
def dataset_urls(query: _QueryParams):
    """
    Get all dataset URLs that satisfy the constraints imposed by the query parameters.
    """
    raise NotImplementedError


@bp.get(
    f"{_URL_PREFIX}/<int:id>",
    responses={"200": DatasetURLRespModel},
    tags=[_TAG],
)
def dataset_url(path: _PathParams):
    """
    Get a dataset URL by ID.
    """
    ds_url = DatasetURLRespModel.from_orm(db.get_or_404(URL, path.id))
    return json_resp_from_str(ds_url.json())
