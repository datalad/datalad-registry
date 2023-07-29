from enum import auto

from pydantic import BaseSettings

from datalad_registry.utils.misc import StrEnum


class OperationMode(StrEnum):
    PRODUCTION = auto()
    DEVELOPMENT = auto()
    TESTING = auto()


class BaseConfig(BaseSettings):
    DATALAD_REGISTRY_OPERATION_MODE: OperationMode = OperationMode.PRODUCTION
    CELERY = {}

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
