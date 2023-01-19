import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

from celery.app.base import Celery
from celery.schedules import crontab
from flask import Flask
from flask.logging import default_handler
from kombu.serialization import register

from datalad_registry import celery, dataset_urls, datasets, overview, root
from datalad_registry.models import db, init_db_command

from .utils.pydantic_json import pydantic_model_dumps, pydantic_model_loads

lgr = logging.getLogger(__name__)


def _setup_logging(level: Union[int, str]) -> None:
    lgr = logging.getLogger("datalad_registry")
    lgr.setLevel(level)
    lgr.addHandler(default_handler)


def setup_celery(app: Flask, celery: Celery) -> Celery:
    celery.conf.beat_schedule = {}
    cache_dir = app.config.get("DATALAD_REGISTRY_DATASET_CACHE")
    if cache_dir:
        celery.conf.beat_schedule["collect_dataset_info"] = {
            "task": "datalad_registry.tasks.collect_dataset_info",
            "schedule": crontab(minute="*/5"),
        }
    else:
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
    app = Flask(
        __name__, instance_path=os.environ.get("DATALAD_REGISTRY_INSTANCE_PATH")
    )
    instance_path = Path(app.instance_path)
    app.config.from_mapping(SQLALCHEMY_TRACK_MODIFICATIONS=False)

    if app.config["ENV"] == "production" and not test_config:
        raise RuntimeError("Not ready yet")
    else:
        config_obj = "datalad_registry.config.DevelopmentConfig"
    app.config.from_object(config_obj)

    app.config.from_envvar("DATALAD_REGISTRY_CONFIG", silent=True)
    if test_config:
        app.config.from_mapping(test_config)

    _setup_logging(app.config["DATALAD_REGISTRY_LOG_LEVEL"])

    instance_path.mkdir(parents=True, exist_ok=True)
    setup_celery(app, celery)
    db.init_app(app)
    app.cli.add_command(init_db_command)
    app.register_blueprint(datasets.bp)
    app.register_blueprint(dataset_urls.bp)
    app.register_blueprint(overview.bp)
    app.register_blueprint(root.bp)
    return app
