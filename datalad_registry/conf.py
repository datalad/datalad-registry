class DefaultConfig:
    CELERY = {}


class ProductionConfig(DefaultConfig):
    pass


class DevelopmentConfig(DefaultConfig):
    pass


class TestingConfig(DefaultConfig):
    pass
