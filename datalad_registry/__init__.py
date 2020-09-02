__version__ = "0.0.0"

from pathlib import Path

from flask import Flask

from datalad_registry import dataset_urls


def create_app():
    app = Flask(__name__)
    instance_path = Path(app.instance_path)
    instance_path.mkdir(parents=True, exist_ok=True)
    app.register_blueprint(dataset_urls.bp)
    return app
