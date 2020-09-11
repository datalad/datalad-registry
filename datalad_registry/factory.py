import logging
import os
from pathlib import Path

from flask import Flask
from flask.logging import default_handler

from datalad_registry import celery
from datalad_registry import dataset_urls
from datalad_registry import db


def _log_level():
    env = os.environ.get("DATALAD_REGISTRY_LOG_LEVEL")
    if env:
        try:
            level = int(env)
        except ValueError:
            level = env.upper()
    else:
        level = "INFO"
    return level


def _setup_logging():
    lgr = logging.getLogger("datalad_registry")
    lgr.setLevel(_log_level())
    lgr.addHandler(default_handler)


def setup_celery(app, celery):
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


def create_app():
    _setup_logging()

    app = Flask(__name__)
    instance_path = Path(app.instance_path)
    broker_url = os.environ.get("CELERY_BROKER_URL",
                                "amqp://localhost:5672")
    app.config.from_mapping(
        CELERY_BROKER_URL=broker_url,
        DATABASE=str(instance_path / "registry.sqlite"))
    instance_path.mkdir(parents=True, exist_ok=True)
    setup_celery(app, celery)
    db.init_app(app)
    app.register_blueprint(dataset_urls.bp)
    return app
