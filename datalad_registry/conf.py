from pydantic import BaseSettings


class DefaultConfig(BaseSettings):
    CELERY = {}


class ProductionConfig(DefaultConfig):
    pass


class DevelopmentConfig(DefaultConfig):
    pass


class TestingConfig(DefaultConfig):
    pass
