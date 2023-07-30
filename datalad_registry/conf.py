from enum import auto
from pathlib import Path

from pydantic import BaseSettings, validator

from datalad_registry.utils.misc import StrEnum

from .utils.pydantic_tls import path_must_be_absolute


class OperationMode(StrEnum):
    PRODUCTION = auto()
    DEVELOPMENT = auto()
    TESTING = auto()
    READ_ONLY = auto()


class BaseConfig(BaseSettings):
    DATALAD_REGISTRY_OPERATION_MODE: OperationMode = OperationMode.PRODUCTION
    DATALAD_REGISTRY_INSTANCE_PATH: Path
    DATALAD_REGISTRY_DATASET_CACHE: Path

    CELERY: dict

    _path_must_be_absolute = validator(
        "DATALAD_REGISTRY_INSTANCE_PATH",
        "DATALAD_REGISTRY_DATASET_CACHE",
        allow_reuse=True,
    )(path_must_be_absolute)

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


class ReadOnlyConfig(BaseConfig):
    """
    Configuration for read-only operation mode

    In this mode, the registry only provides read-only access through its web service
    """

    # The Celery service is not available in read-only mode.
    # The following are just dummy values to serve as defaults to satisfy
    # the configuration requirements and make the corresponding fields optional.
    DATALAD_REGISTRY_DATASET_CACHE: Path = Path("/dummy/path")
    CELERY = {}
