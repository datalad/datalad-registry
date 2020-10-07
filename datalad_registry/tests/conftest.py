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


@pytest.fixture
def client():
    config = {"CELERY_BEAT_SCHEDULE": {},
              "CELERY_TASK_ALWAYS_EAGER": True,
              "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
              "TESTING": True}
    app = create_app(config)
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
