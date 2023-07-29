from pydantic import BaseSettings


class DefaultConfig(BaseSettings):
    CELERY = {}

    class Config:
        case_sensitive = True


class ProductionConfig(DefaultConfig):
    pass


class DevelopmentConfig(DefaultConfig):
    pass


class TestingConfig(DefaultConfig):
    pass
