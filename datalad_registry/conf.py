from enum import auto
from pathlib import Path

from pydantic import BaseSettings, validator

from datalad_registry.utils.misc import StrEnum


class OperationMode(StrEnum):
    PRODUCTION = auto()
    DEVELOPMENT = auto()
    TESTING = auto()


class BaseConfig(BaseSettings):
    DATALAD_REGISTRY_OPERATION_MODE: OperationMode = OperationMode.PRODUCTION
    DATALAD_REGISTRY_INSTANCE_PATH: Path
    DATALAD_REGISTRY_DATASET_CACHE: Path

    CELERY = {}

    # U100: Unused argument; B902: Invalid first argument 'cls'
    @validator("DATALAD_REGISTRY_INSTANCE_PATH", "DATALAD_REGISTRY_DATASET_CACHE")
    def path_must_be_absolute(cls, v: Path) -> Path:  # noqa: U100,B902
        if not v.is_absolute():
            raise ValueError("Path must be absolute")
        return v

    class Config:
        case_sensitive = True


class ProductionConfig(BaseConfig):
    CELERY = dict(
        broker_url="",  # TODO: to be specified
        result_backend="",  # TODO: to be specified
        task_ignore_result=True,
    )


class DevelopmentConfig(BaseConfig):
    CELERY = dict(
        broker_url="",  # TODO: to be specified
        result_backend="",  # TODO: to be specified
        task_ignore_result=True,
    )


class TestingConfig(BaseConfig):
    pass
