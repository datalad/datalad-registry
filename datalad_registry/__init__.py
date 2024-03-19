from importlib.metadata import version
from pathlib import Path

from celery import Celery, Task
from flask import Flask, request
from flask_openapi3 import Info, OpenAPI
from kombu.serialization import register
from werkzeug.exceptions import HTTPException

from . import overview, root
from .conf import OperationMode, compile_config_from_env
from .models import db, init_db_command, migrate
from .utils.pydantic_json import pydantic_dumps, pydantic_loads

__version__ = version("datalad-registry")


def create_app() -> Flask:
    """
    Factory function for producing Flask app
    """

    config = compile_config_from_env()

    app = OpenAPI(
        __name__,
        info=Info(title="Datalad Registry API", version="2.0"),
        instance_path=str(config.DATALAD_REGISTRY_INSTANCE_PATH),
        instance_relative_config=True,
    )

    app.config.from_object(config)

    # Allows overriding the Flask app config in an ad hoc manner
    # with the "FLASK_" prefix in env var names
    app.config.from_prefixed_env()

    # Ensure instance path exists
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    if app.config["DATALAD_REGISTRY_OPERATION_MODE"] is not OperationMode.READ_ONLY:
        # Integrate a Celery app
        celery_init_app(app)

    # Integrate Flask-SQLAlchemy
    db.init_app(app)

    # Integrate Flask-Migrate
    migrate.init_app(app, db)

    # Register CLI commands
    app.cli.add_command(init_db_command)

    # Register Web UI blueprints
    app.register_blueprint(overview.bp)
    app.register_blueprint(root.bp)

    from .blueprints.api import HTTPExceptionResp
    from .blueprints.api.dataset_urls import bp as dataset_urls_bp
    from .blueprints.api.url_metadata import bp as url_metadata_bp

    # Register API blueprints
    app.register_api(dataset_urls_bp)
    app.register_api(url_metadata_bp)

    @app.errorhandler(HTTPException)
    def handle_exception(e):
        """
        Convert all HTTPExceptions to JSON responses for the API paths
        while conforming to the API paths' OpenAPI specification.
        """
        if request.path.startswith("/api/"):
            # start with the correct headers and status code from the error
            response = e.get_response()
            # replace the body with JSON
            response.data = HTTPExceptionResp(
                code=e.code, name=e.name, description=e.description
            ).json()
            response.content_type = "application/json"
            return response
        else:
            return e

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
    # Pydantic models and other supported types by Pydantic for JSON serialization
    register(
        "pydantic_json",
        pydantic_dumps,
        pydantic_loads,
        content_type="application/x-pydantic-json",
        content_encoding="utf-8",
    )

    # Set the Celery app to use the JSON serializer registered above
    celery_app.conf.update(
        accept_content=["pydantic_json"],
        task_serializer="pydantic_json",
        result_serializer="pydantic_json",
    )

    celery_app.set_default()

    flask_app.extensions["celery"] = celery_app
    return celery_app
