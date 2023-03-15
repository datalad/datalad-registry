import os

import pytest
from sqlalchemy.engine.url import URL

from datalad_registry.factory import create_app


@pytest.fixture
def flask_app(monkeypatch, tmp_path):
    """
    The fixture of the datalad_registry Flask app set up with the database of the test
    environment that is cleanly initialized for each test
    """
    instance_path = tmp_path / "instance"
    cache_path = tmp_path / "cache"

    instance_path.mkdir()
    cache_path.mkdir()

    monkeypatch.setenv("DATALAD_REGISTRY_INSTANCE_PATH", str(instance_path))

    test_config = {
        "DATALAD_REGISTRY_DATASET_CACHE": str(cache_path),
        "SQLALCHEMY_DATABASE_URI": str(
            URL.create(
                drivername="postgresql",
                host="127.0.0.1",
                port=5432,
                database="dlreg",
                username="dlreg",
                password=os.environ["DATALAD_REGISTRY_PASSWORD"],
            )
        ),
    }

    app = create_app(test_config)

    from datalad_registry.models import db

    # Ensure the Flask app is one with a cleanly initialized database
    with app.app_context():
        db.drop_all()
        db.create_all()

    return app


@pytest.fixture
def flask_client(flask_app):
    """
    The fixture of the test client of flask_app
    """
    return flask_app.test_client()


@pytest.fixture
def flask_cli_runner(flask_app):
    """
    The fixture of the test cli runner of flask_app
    """
    return flask_app.test_cli_runner()
