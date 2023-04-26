import os

from datalad import api as dl
from datalad.api import Dataset
import pytest
from pytest import TempPathFactory
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
        "TESTING": True,
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


@pytest.fixture(scope="session")
def empty_ds_annex(tmp_path_factory) -> Dataset:
    """
    An empty dataset that is a git-annex repository
    """
    return dl.create(path=tmp_path_factory.mktemp("empty_ds_annex"))


@pytest.fixture(scope="session")
def empty_ds_non_annex(tmp_path_factory) -> Dataset:
    """
    An empty dataset that is not a git-annex repository
    """
    return dl.create(path=tmp_path_factory.mktemp("empty_ds_non_annex"), annex=False)


def two_files_ds(annex: bool, tmp_path_factory: TempPathFactory) -> Dataset:
    """
    A dataset with two simple files
    """
    ds: Dataset = dl.create(
        path=tmp_path_factory.mktemp(
            f"two_files_ds_{'annex' if annex else 'non_annex'}"
        ),
        annex=annex,
    )

    file_names = ["file1.txt", "file2.txt"]
    for file_name in file_names:
        with open(ds.pathobj / file_name, "w") as f:
            f.write(f"Hello in {file_name}\n")

    ds.save(message=f"Add {', '.join(file_names)}")
    return ds


@pytest.fixture(scope="session")
def two_files_ds_annex(tmp_path_factory) -> Dataset:
    """
    A dataset with two simple files that is a git-annex repository
    """
    return two_files_ds(annex=True, tmp_path_factory=tmp_path_factory)


@pytest.fixture(scope="session")
def two_files_ds_non_annex(tmp_path_factory) -> Dataset:
    """
    A dataset with two simple files that is not a git-annex repository
    """
    return two_files_ds(annex=False, tmp_path_factory=tmp_path_factory)
