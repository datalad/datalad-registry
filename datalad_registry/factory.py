import logging
import os
from pathlib import Path

from celery.schedules import crontab
from flask import Flask
from flask.logging import default_handler

from datalad_registry import celery
from datalad_registry import datasets
from datalad_registry import dataset_urls
from datalad_registry import overview
from datalad_registry import root
from datalad_registry.models import db
from datalad_registry.models import init_db_command

lgr = logging.getLogger(__name__)


def _setup_logging(level):
    lgr = logging.getLogger("datalad_registry")
    lgr.setLevel(level)
    lgr.addHandler(default_handler)


def setup_celery(app, celery):
    celery.conf.beat_schedule = {}
    cache_dir = app.config.get("DATALAD_REGISTRY_DATASET_CACHE")
    if cache_dir:
        celery.conf.beat_schedule["collect_dataset_info"] = {
            "task": "datalad_registry.tasks.collect_dataset_info",
            "schedule": crontab(minute="*/5")}
    else:
        lgr.debug("DATALAD_REGISTRY_DATASET_CACHE isn't configured. "
                  "Not registering periodic tasks that depend on it")

    celery.config_from_object(app.config, namespace="CELERY")

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


def create_app(test_config=None, instance_path=None):
    app = Flask(
        __name__,
        instance_path=os.environ.get("DATALAD_REGISTRY_INSTANCE_PATH"))
    instance_path = Path(app.instance_path)
    db_uri = "sqlite:///" + str(instance_path / "registry.sqlite")
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=db_uri,
        SQLALCHEMY_TRACK_MODIFICATIONS=False)

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
