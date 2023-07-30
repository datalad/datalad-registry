from enum import auto
from pathlib import Path
from typing import Any

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

    # Celery related configuration
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    CELERY_TASK_IGNORE_RESULT: bool

    # noinspection PyPep8Naming
    @property
    def CELERY(self) -> dict[str, Any]:
        return dict(
            broker_url=self.CELERY_BROKER_URL,
            result_backend=self.CELERY_RESULT_BACKEND,
            task_ignore_result=self.CELERY_TASK_IGNORE_RESULT,
        )

    _path_must_be_absolute = validator(
        "DATALAD_REGISTRY_INSTANCE_PATH",
        "DATALAD_REGISTRY_DATASET_CACHE",
        allow_reuse=True,
    )(path_must_be_absolute)

    class Config:
        case_sensitive = True


class ProductionConfig(BaseConfig):
    CELERY_TASK_IGNORE_RESULT: bool = True


class DevelopmentConfig(BaseConfig):
    CELERY_TASK_IGNORE_RESULT: bool = True


class TestingConfig(BaseConfig):
    CELERY_TASK_IGNORE_RESULT: bool = True


class ReadOnlyConfig(BaseConfig):
    """
    Configuration for read-only operation mode

    In this mode, the registry only provides read-only access through its web service
    """

    # The Celery service is not available in read-only mode.
    # The following are just dummy values to serve as defaults to satisfy
    # the configuration requirements and make the corresponding fields optional.
    DATALAD_REGISTRY_DATASET_CACHE: Path = Path("/dummy/path")

    CELERY_BROKER_URL: str = "dummy://"
    CELERY_RESULT_BACKEND: str = "dummy://"
    CELERY_TASK_IGNORE_RESULT: bool = True
    CELERY = {}
