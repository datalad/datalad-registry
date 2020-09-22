import uuid
from random import Random

import pytest

from datalad_registry.factory import create_app
from datalad_registry.models import db

random = Random()
random.seed("datalad-registry")


@pytest.fixture
def dsid():
    return str(uuid.UUID(int=random.getrandbits(128)))


@pytest.fixture(scope="session")
def client(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("db")
    db_uri = "sqlite:///" + str(tmp_path / "registry.sqlite3")
    config = {"CELERY_ALWAYS_EAGER": True,
              "SQLALCHEMY_DATABASE_URI": db_uri,
              "TESTING": True}
    app = create_app(config)
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
