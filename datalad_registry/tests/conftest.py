import pytest

from datalad_registry.db import init_db
from datalad_registry.factory import create_app


@pytest.fixture
def client(tmp_path):
    config = {"CELERY_ALWAYS_EAGER": True,
              "DATABASE": str(tmp_path / "registry.sqlite3"),
              "TESTING": True}
    app = create_app(config)
    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client
