# todo: Nothing defined in this module seems to be used anywhere else

import os
from typing import Union

from sqlalchemy.engine.url import URL


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
    CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "amqp://localhost:5672")
    CELERY_result_backend = os.environ["CELERY_RESULT_BACKEND"]
    DATALAD_REGISTRY_DATASET_CACHE = os.environ.get("DATALAD_REGISTRY_DATASET_CACHE")
    DATALAD_REGISTRY_LOG_LEVEL = _log_level()


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = str(
        URL.create(
            drivername="postgresql",
            host=os.environ.get("DATALAD_REGISTRY_POSTGRES_HOST", "localhost"),
            port=5432,
            database="dlreg",
            username="dlreg",
            password=os.environ["DATALAD_REGISTRY_PASSWORD"],
        )
    )


# TODO: ProductionConfig
# from sqlalchemy.engine.url import URL
# SQLALCHEMY_DATABASE_URI=str(URL.create(
#     drivername = "postgresql",
#     host       = "db",
#     port       = 5432,
#     database   = "dlreg",
#     username   = "dlreg",
#     password   = os.environ.get("POSTGRES_PASSWORD", "postgres"),
# ))
