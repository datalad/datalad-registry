import os


class Config(object):
    CELERY_BROKER_URL = os.environ.get(
        "CELERY_BROKER_URL", "amqp://localhost:5672")


class DevelopmentConfig(Config):
    DEBUG = True


# TODO: ProductionConfig
