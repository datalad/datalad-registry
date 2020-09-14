import pytest

from datalad_registry import celery
from datalad_registry.db import init_db
from datalad_registry.factory import create_app
from datalad_registry.factory import setup_celery


@pytest.fixture
def client(tmp_path):
    config = {"CELERY_ALWAYS_EAGER": True,
              "DATABASE": str(tmp_path / "registry.sqlite3"),
              "TESTING": True}
    app = create_app(config)
    setup_celery(app, celery)
    celery.conf.update()
    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client
