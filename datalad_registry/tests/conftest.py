import uuid
from random import Random

import pytest

from datalad_registry.db import init_db
from datalad_registry.factory import create_app

random = Random()
random.seed("datalad-registry")


@pytest.fixture
def dsid():
    return str(uuid.UUID(int=random.getrandbits(128)))


@pytest.fixture(scope="session")
def client(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("db")
    config = {"CELERY_ALWAYS_EAGER": True,
              "DATABASE": str(tmp_path / "registry.sqlite3"),
              "TESTING": True}
    app = create_app(config)
    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client
