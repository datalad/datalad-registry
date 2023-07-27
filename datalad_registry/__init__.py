import sys

from celery import Celery, Task
from flask import Flask
from kombu.serialization import register

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
    app = Flask(__name__)
    app.config.from_mapping(
        CELERY=dict(
            broker_url="to be specified",
            result_backend="to be specified",
            task_ignore_result=True,
        ),
    )
    app.config.from_prefixed_env()
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
