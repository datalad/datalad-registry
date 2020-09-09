__version__ = "0.0.0"

import logging
import os
from pathlib import Path

from flask import Flask
from flask.logging import default_handler

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
    lgr = logging.getLogger(__name__)
    lgr.setLevel(_log_level())
    lgr.addHandler(default_handler)


def create_app():
    _setup_logging()

    app = Flask(__name__)
    instance_path = Path(app.instance_path)
    app.config.from_mapping(
        DATABASE=str(instance_path / "registry.sqlite"))
    instance_path.mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    app.register_blueprint(dataset_urls.bp)
    return app
