from collections import namedtuple
import uuid
from random import Random

import pytest

from datalad_registry.factory import create_app
from datalad_registry.models import db

random = Random()
random.seed("datalad-registry")

AppInstance = namedtuple("AppInstance", ["app", "db", "client"])


@pytest.fixture
def dsid():
    return str(uuid.UUID(int=random.getrandbits(128)))


@pytest.fixture
def app_instance():
    """Fixture that provides the application, database, and client.

    If you just need the client, you can use the `client` fixture
    instead.

    Yields
    ------
    AppInstance namedtuple with app, db, and client fields.
    """
    config = {"CELERY_BEAT_SCHEDULE": {},
              "CELERY_TASK_ALWAYS_EAGER": True,
              "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
              "TESTING": True}
    app = create_app(config)
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield AppInstance(app, db, client)


@pytest.fixture
def client(app_instance):
    """Fixture that provides client.

    If you need to access to the application or database, use the
    `app_instance` fixture instead.
    """
    yield app_instance.client
