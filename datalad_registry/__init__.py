import os
from pathlib import Path
import sys

from celery import Celery, Task
from flask import Flask
from flask_openapi3 import Info, OpenAPI
from kombu.serialization import register

from .conf import (
    BaseConfig,
    DevelopmentConfig,
    OperationMode,
    ProductionConfig,
    ReadOnlyConfig,
    TestingConfig,
)
from .utils.pydantic_json import pydantic_model_dumps, pydantic_model_loads

if sys.version_info[:2] < (3, 8):
    from importlib_metadata import version
else:
    from importlib.metadata import version

__version__ = version("datalad-registry")

celery = Celery("datalad_registry")


def create_app() -> Flask:
    """
    Factory function for producing Flask app
    """
    app = OpenAPI(
        __name__,
        info=Info(title="Datalad Registry API", version="2.0"),
        instance_path=os.environ["DATALAD_REGISTRY_INSTANCE_PATH"],
        instance_relative_config=True,
    )

    operation_mode = BaseConfig().DATALAD_REGISTRY_OPERATION_MODE

    if operation_mode is OperationMode.PRODUCTION:
        config = ProductionConfig()
    elif operation_mode is OperationMode.READ_ONLY:
        config = ReadOnlyConfig()
    elif operation_mode is OperationMode.DEVELOPMENT:
        config = DevelopmentConfig()
    elif operation_mode is OperationMode.TESTING:
        config = TestingConfig()
    else:
        # This should never happen
        raise ValueError(f"Unexpected operation mode: {operation_mode!r}")

    app.config.from_object(config)

    # Allows overriding the Flask app config in an ad hoc manner
    # with the "FLASK_" prefix in env var names
    app.config.from_prefixed_env()

    # Ensure instance path exists
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    celery_init_app(app)
    return app


def celery_init_app(flask_app: Flask) -> Celery:
    """
    Factory function for producing a Celery app that integrates with a given Flask app
    :param flask_app: The given Flask app
    :return: The Celery app that is integrated with the Flask app. In particular,
             the produced Celery app will have tasks that operate within the
             app context of the Flask app.
    Note: The produced Celery app is configured via the value for the `CELERY` key
          in the `config` of the given Flask app.

    Note: This function sets `flask_app.extensions["celery"]`
          to the produced Celery app.

    Note: This function is adapted from
          https://flask.palletsprojects.com/en/2.3.x/patterns/celery/#integrate-celery-with-flask
    """

    class FlaskTask(Task):
        def __call__(self, *args, **kwargs):
            with flask_app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(flask_app.name, task_cls=FlaskTask)
    celery_app.config_from_object(flask_app.config["CELERY"])

    # Register JSON encoding and decoding functions with additional support of
    # Pydantic models as a serializer
    register(
        "pydantic_json",
        pydantic_model_dumps,
        pydantic_model_loads,
        content_type="application/x-pydantic-json",
        content_encoding="utf-8",
    )

    # Set the Celery app to use the JSON serializer with support for Pydantic models
    celery_app.conf.update(
        accept_content=["pydantic_json"],
        task_serializer="pydantic_json",
        result_serializer="pydantic_json",
    )

    celery_app.set_default()

    flask_app.extensions["celery"] = celery_app
    return celery_app
