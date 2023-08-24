# This file provides Celery commands access to the Celery app created through
# the factory functions in datalad_registry/__init__.py

from . import create_app

flask_app = create_app()
celery_app = flask_app.extensions["celery"]
