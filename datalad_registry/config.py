import os
from typing import Union


def _log_level() -> Union[str, int]:
    env = os.environ.get("DATALAD_REGISTRY_LOG_LEVEL")
    level: Union[str, int]
    if env:
        try:
            level = int(env)
        except ValueError:
            level = env.upper()
    else:
        level = "INFO"
    return level


class Config(object):
    CELERY_BROKER_URL = os.environ.get(
        "CELERY_BROKER_URL", "amqp://localhost:5672")
    DATALAD_REGISTRY_DATASET_CACHE = os.environ.get(
        "DATALAD_REGISTRY_DATASET_CACHE")
    DATALAD_REGISTRY_LOG_LEVEL = _log_level()


class DevelopmentConfig(Config):
    DEBUG = True


# TODO: ProductionConfig
