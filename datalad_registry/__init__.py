import sys

from celery import Celery, Task
from flask import Flask

if sys.version_info[:2] < (3, 8):
    from importlib_metadata import version
else:
    from importlib.metadata import version

__version__ = version("datalad-registry")

celery = Celery("datalad_registry")


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
    celery_app.set_default()
    flask_app.extensions["celery"] = celery_app
    return celery_app
