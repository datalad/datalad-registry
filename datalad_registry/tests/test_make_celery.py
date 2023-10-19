from celery import Celery
import pytest


@pytest.mark.usefixtures("set_test_env")
def test_celery_app_instantiation():
    """
    Test that the Celery app is instantiated correctly.
    """
    from datalad_registry.make_celery import celery_app, flask_app

    assert celery_app is flask_app.extensions["celery"]
    assert isinstance(celery_app, Celery)
