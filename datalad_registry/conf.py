from enum import auto

from pydantic import BaseSettings

from datalad_registry.utils.misc import StrEnum


class OperationMode(StrEnum):
    PRODUCTION = auto()
    DEVELOPMENT = auto()
    TESTING = auto()


class DefaultConfig(BaseSettings):
    DATALAD_REGISTRY_OPERATION_MODE: OperationMode = OperationMode.PRODUCTION
    CELERY = {}

    class Config:
        case_sensitive = True


class ProductionConfig(DefaultConfig):
    pass


class DevelopmentConfig(DefaultConfig):
    pass


class TestingConfig(DefaultConfig):
    pass
