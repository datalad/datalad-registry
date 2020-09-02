__version__ = "0.0.0"

from pathlib import Path

from flask import Flask


def create_app():
    app = Flask(__name__)
    instance_path = Path(app.instance_path)
    instance_path.mkdir(parents=True, exist_ok=True)
    return app
