import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

from celery.app.base import Celery
from flask import Flask, request
from flask.logging import default_handler
from flask_openapi3 import Info, OpenAPI
from kombu.serialization import register
from werkzeug.exceptions import HTTPException

from datalad_registry import celery, dataset_urls, datasets, overview, root
from datalad_registry.models import db, init_db_command, migrate

from .utils.pydantic_json import pydantic_model_dumps, pydantic_model_loads

FLASK_APP_NAME = "datalad_registry"

lgr = logging.getLogger(__name__)


def _setup_logging(level: Union[int, str]) -> None:
    lgr = logging.getLogger("datalad_registry")
    lgr.setLevel(level)
    lgr.addHandler(default_handler)


def setup_celery(app: Flask, celery: Celery) -> Celery:
    celery.conf.beat_schedule = {}
    cache_dir = app.config.get("DATALAD_REGISTRY_DATASET_CACHE")
    if cache_dir is None:
        lgr.debug(
            "DATALAD_REGISTRY_DATASET_CACHE isn't configured. "
            "Not registering periodic tasks that depend on it"
        )

    celery.config_from_object(app.config, namespace="CELERY")

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
    celery.conf.update(
        accept_content=["pydantic_json"],
        task_serializer="pydantic_json",
        result_serializer="pydantic_json",
    )

    class ContextTask(celery.Task):  # type: ignore
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


def create_app(test_config: Optional[Dict[str, Any]] = None) -> Flask:
    api_info = Info(title="Datalad Registry API", version="2.0")
    app = OpenAPI(
        FLASK_APP_NAME,
        instance_path=os.environ.get("DATALAD_REGISTRY_INSTANCE_PATH"),
        info=api_info,
    )
    instance_path = Path(app.instance_path)
    app.config.from_mapping(SQLALCHEMY_TRACK_MODIFICATIONS=False)

    config_obj = "datalad_registry.config.DevelopmentConfig"
    app.config.from_object(config_obj)

    app.config.from_envvar("DATALAD_REGISTRY_CONFIG", silent=True)
    if test_config:
        app.config.from_mapping(test_config)

    _setup_logging(app.config["DATALAD_REGISTRY_LOG_LEVEL"])

    instance_path.mkdir(parents=True, exist_ok=True)
    setup_celery(app, celery)
    db.init_app(app)
    migrate.init_app(app, db)
    app.cli.add_command(init_db_command)
    app.register_blueprint(datasets.bp)
    app.register_blueprint(dataset_urls.bp)
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
            response.data = json.dumps(
                HTTPExceptionResp(
                    code=e.code, name=e.name, description=e.description
                ).dict()
            )
            response.content_type = "application/json"
            return response
        else:
            return e

    return app
