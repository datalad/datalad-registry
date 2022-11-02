from collections import namedtuple
import os
from pathlib import Path
import random
import shutil
import string
from subprocess import PIPE, run
from time import sleep

import pytest
from sqlalchemy.engine.url import URL

from datalad_registry.factory import create_app
from datalad_registry.models import db
from datalad_registry.tests.utils import make_ds_id

AppInstance = namedtuple("AppInstance", ["app", "db"])


@pytest.fixture
def ds_id():
    """Return a random dataset ID."""
    return make_ds_id()


@pytest.fixture(scope="session")
def cache_dir(tmp_path_factory):
    """Return temporary location of DATALAD_REGISTRY_DATASET_CACHE."""
    return tmp_path_factory.mktemp("cache_dir")


LOCAL_DOCKER_DIR = Path(__file__).with_name("data") / "datalad-registry-db"
LOCAL_DOCKER_ENV = LOCAL_DOCKER_DIR.name


@pytest.fixture(scope="session")
def dockerdb(request):
    if shutil.which("docker-compose") is None:
        pytest.skip("docker-compose required")
    if os.name != "posix":
        pytest.skip("Docker images require Unix host")

    if "DATALAD_REGISTRY_PASSWORD" not in os.environ:
        os.environ["DATALAD_REGISTRY_PASSWORD"] = "".join(
            random.choices(string.printable, k=32)
        )

    dburl = str(
        URL.create(
            drivername="postgresql",
            host="127.0.0.1",
            port=5432,
            database="dlreg",
            username="dlreg",
            password=os.environ["DATALAD_REGISTRY_PASSWORD"],
        )
    )

    if request.config.getoption("--devserver"):
        yield dburl
        return

    persist = os.environ.get("DATALAD_REGISTRY_PERSIST_DOCKER_COMPOSE")
    try:
        run(["docker-compose", "up", "-d"], cwd=str(LOCAL_DOCKER_DIR), check=True)
        for _ in range(10):
            health = run(
                [
                    "docker",
                    "inspect",
                    "--format={{.State.Health.Status}}",
                    f"{LOCAL_DOCKER_ENV}_db_1",
                ],
                stdout=PIPE,
                check=True,
                universal_newlines=True,
            ).stdout.strip()
            if health == "healthy":
                break
            sleep(3)
        else:
            raise RuntimeError("Database container did not initialize in time")
        yield dburl
    finally:
        if persist in (None, "0"):
            run(["docker-compose", "down", "-v"], cwd=str(LOCAL_DOCKER_DIR), check=True)


@pytest.fixture(scope="session")
def _app_instance(dockerdb, tmp_path_factory, cache_dir):
    if "DATALAD_REGISTRY_INSTANCE_PATH" not in os.environ:
        os.environ["DATALAD_REGISTRY_INSTANCE_PATH"] = str(
            tmp_path_factory.mktemp("instance")
        )
    config = {
        "CELERY_BEAT_SCHEDULE": {},
        "CELERY_TASK_ALWAYS_EAGER": True,
        "DATALAD_REGISTRY_DATASET_CACHE": str(cache_dir),
        "SQLALCHEMY_DATABASE_URI": dockerdb,
        "TESTING": True,
    }
    # crude way to add timeout for connections which might be hanging
    import socket

    socket.setdefaulttimeout(2)  # seconds
    app = create_app(config)
    yield AppInstance(app, db)


@pytest.fixture
def app_instance(_app_instance):
    """Fixture that provides the application, database, and client.

    If you just need the client, you can use the `client` fixture
    instead.

    Yields
    ------
    AppInstance namedtuple with app, db, and client fields.
    """
    with _app_instance.app.app_context():
        db.drop_all()
        db.create_all()
        yield _app_instance


@pytest.fixture
def client(app_instance):
    """Fixture that provides client.

    If you need to access to the application or database, use the
    `app_instance` fixture instead.
    """
    yield app_instance.app.test_client()
