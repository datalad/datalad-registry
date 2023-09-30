from enum import auto
from pathlib import Path
from typing import Any, Literal, Union

from pydantic import BaseSettings, NonNegativeInt, PostgresDsn, validator

from datalad_registry.utils.misc import StrEnum

from .utils.pydantic_tls import path_must_be_absolute


class OperationMode(StrEnum):
    PRODUCTION = auto()
    DEVELOPMENT = auto()
    TESTING = auto()
    READ_ONLY = auto()


class OperationConfig(BaseSettings):
    DATALAD_REGISTRY_OPERATION_MODE: OperationMode


class BaseConfig(OperationConfig):
    DATALAD_REGISTRY_INSTANCE_PATH: Path
    DATALAD_REGISTRY_DATASET_CACHE: Path

    # URL check dispatcher related configuration
    DATALAD_REGISTRY_MIN_CHK_INTERVAL_PER_URL: NonNegativeInt = 3600  # seconds
    DATALAD_REGISTRY_MAX_FAILED_CHKS_PER_URL: NonNegativeInt = 10
    DATALAD_REGISTRY_MAX_URL_CHKS_ISSUED_PER_CYCLE: NonNegativeInt = 10

    # Metadata extractors to use
    DATALAD_REGISTRY_METADATA_EXTRACTORS: list[str] = [
        "metalad_core",
        "metalad_studyminimeta",
        "datacite_gin",
        "bids_dataset",
    ]

    # === worker, Celery, related configuration  ===
    CELERY_BROKER_URL: Union[str, list[str]]
    CELERY_RESULT_BACKEND: str
    CELERY_BEAT_SCHEDULE: dict[str, dict[str, Any]] = {
        "url-check-dispatcher": {
            "task": "datalad_registry.tasks.url_chk_dispatcher",
            "schedule": 60.0,
            "options": {"expires": 60.0},
        }
    }

    # noinspection PyPep8Naming
    @property
    def CELERY(self) -> dict[str, Any]:
        return dict(
            broker_url=self.CELERY_BROKER_URL,
            result_backend=self.CELERY_RESULT_BACKEND,
            beat_schedule=self.CELERY_BEAT_SCHEDULE,
            task_ignore_result=True,
            worker_max_tasks_per_child=1000,
            worker_max_memory_per_child=1000 * 500,  # 500 MB
        )

    # =============================================

    SQLALCHEMY_DATABASE_URI: PostgresDsn

    TESTING: bool = False

    _path_must_be_absolute = validator(
        "DATALAD_REGISTRY_INSTANCE_PATH",
        "DATALAD_REGISTRY_DATASET_CACHE",
        allow_reuse=True,
    )(path_must_be_absolute)

    class Config:
        case_sensitive = True


class ProductionConfig(BaseConfig):
    # Restrict to operation mode appropriate for this type of configuration
    DATALAD_REGISTRY_OPERATION_MODE: Literal[OperationMode.PRODUCTION]


class DevelopmentConfig(BaseConfig):
    # Restrict to operation mode appropriate for this type of configuration
    DATALAD_REGISTRY_OPERATION_MODE: Literal[OperationMode.DEVELOPMENT]


class TestingConfig(BaseConfig):
    # Restrict to operation mode appropriate for this type of configuration
    DATALAD_REGISTRY_OPERATION_MODE: Literal[OperationMode.TESTING]

    TESTING: bool = True


class ReadOnlyConfig(BaseConfig):
    """
    Configuration for read-only operation mode

    In this mode, the registry only provides read-only access through its web service
    """

    # Restrict to operation mode appropriate for this type of configuration
    DATALAD_REGISTRY_OPERATION_MODE: Literal[OperationMode.READ_ONLY]

    # The Celery service is not available in read-only mode.
    # The following are just dummy values to serve as defaults to satisfy
    # the configuration requirements and make the corresponding fields optional.
    DATALAD_REGISTRY_DATASET_CACHE: Path = Path("/dummy/path")

    CELERY_BROKER_URL: str = "dummy://"
    CELERY_RESULT_BACKEND: str = "dummy://"

    @property
    def CELERY(self) -> dict[str, Any]:
        return {}


operation_mode_to_config_cls = {
    OperationMode.PRODUCTION: ProductionConfig,
    OperationMode.DEVELOPMENT: DevelopmentConfig,
    OperationMode.TESTING: TestingConfig,
    OperationMode.READ_ONLY: ReadOnlyConfig,
}


def compile_config_from_env() -> BaseConfig:
    """
    Compile a configuration object from the environment variables that contains
    all and only the attributes (setting options) required to run the application
    """
    operation_mode = OperationConfig().DATALAD_REGISTRY_OPERATION_MODE

    config_cls = operation_mode_to_config_cls.get(operation_mode)

    if config_cls is not None:
        return config_cls()
    else:
        # This should never happen
        raise ValueError(f"Unexpected operation mode: {operation_mode!r}")
