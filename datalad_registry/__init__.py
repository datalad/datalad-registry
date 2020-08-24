__version__ = "0.0.0"

from pathlib import Path

from flask import Flask

from datalad_registry import dataset_urls
from datalad_registry import db


def create_app():
    app = Flask(__name__)
    instance_path = Path(app.instance_path)
    app.config.from_mapping(
        DATABASE=str(instance_path / "registry.sqlite"))
    instance_path.mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    app.register_blueprint(dataset_urls.bp)
    return app
