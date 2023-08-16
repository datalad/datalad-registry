from datetime import datetime

from celery import Celery
from datalad import api as dl
from datalad.api import Dataset
import pytest
from pytest import TempPathFactory

from datalad_registry import create_app

# noinspection PyPep8Naming
from datalad_registry.models import RepoUrl, URLMetadata, db


@pytest.fixture
def flask_app(tmp_path, monkeypatch):
    """
    The fixture of the datalad_registry Flask app set up with the database of the test
    environment
    """
    instance_path = tmp_path / "instance"
    cache_path = tmp_path / "cache"

    monkeypatch.setenv("DATALAD_REGISTRY_OPERATION_MODE", "TESTING")
    monkeypatch.setenv("DATALAD_REGISTRY_INSTANCE_PATH", str(instance_path))
    monkeypatch.setenv("DATALAD_REGISTRY_DATASET_CACHE", str(cache_path))

    app = create_app()

    # Reset the database
    with app.app_context():
        db.drop_all()
        db.create_all()

    yield app

    with app.app_context():
        celery_app: Celery = app.extensions["celery"]
        for pool in (
            celery_app.pool,
            celery_app.backend.result_consumer,
            celery_app.backend.client,
        ):
            if pool is not None:
                pool.close()


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


@pytest.fixture
def populate_with_2_dataset_urls(flask_app):
    """
    Populate the url table with 2 DatasetURLs, at position 1 and 3.
    """

    dataset_url1 = RepoUrl(url="https://example.com")
    dataset_url2 = RepoUrl(url="https://docs.datalad.org")
    dataset_url3 = RepoUrl(url="/foo/bar")

    with flask_app.app_context():
        for url in [dataset_url1, dataset_url2, dataset_url3]:
            db.session.add(url)
        db.session.commit()

        db.session.delete(dataset_url2)
        db.session.commit()


@pytest.fixture
def populate_with_dataset_urls(flask_app) -> list[str]:
    """
    Populate the url table with a list of DatasetURLs.

    Returns: The list of DatasetURLs that were added to the database
    """

    urls = [
        RepoUrl(
            url="https://www.example.com",
            ds_id="2a0b7b7b-a984-4c4a-844c-be3132291d7b",
            head_describe="1234",
            annex_key_count=20,
            annexed_files_in_wt_count=200,
            annexed_files_in_wt_size=1000,
            git_objects_kb=110,
            last_update_dt=datetime(2008, 7, 18, 18, 34, 32),
            chk_req_dt=datetime(2008, 7, 18, 18, 34, 34),
            processed=True,
            cache_path="8c8/fff/e01f2142d88690d92144b00af0",
        ),
        RepoUrl(
            url="http://www.datalad.org",
            ds_id="2a0b7b7b-a984-4c4a-844c-be3132291d7c",
            head_describe="1234",
            annex_key_count=40,
            annexed_files_in_wt_count=100,
            annexed_files_in_wt_size=400,
            git_objects_kb=1100,
            last_update_dt=datetime(2009, 6, 18, 18, 34, 32),
            # chk_req_dt=None, # Commenting this out to allow `chk_req_dt` to default
            processed=True,
            cache_path="72e/cd9/cc10534e2a9f551e32119e0e60",
        ),
        RepoUrl(
            url="https://handbook.datalad.org",
            ds_id="2a0b7b7b-a984-4c4a-844c-be3132291a7c",
            head_describe="1234",
            annex_key_count=90,
            annexed_files_in_wt_count=490,
            annexed_files_in_wt_size=1000_000,
            git_objects_kb=4000,
            last_update_dt=datetime(2004, 6, 18, 18, 34, 32),
            chk_req_dt=datetime(2004, 6, 19, 18, 34, 34),
            processed=True,
            cache_path="72e/4e5/4184da47e282c02ae7e568ba74",
        ),
        RepoUrl(
            url="https://www.dandiarchive.org",
            processed=False,
            cache_path="a/b/c",
        ),
    ]

    with flask_app.app_context():
        for url in urls:
            db.session.add(url)
        db.session.commit()

        return [url.url for url in urls]


@pytest.fixture
def populate_with_url_metadata(
    populate_with_dataset_urls,  # noqa: U100 (unused argument)
    flask_app,
):
    """
    Populate the url_metadata table with a list of metadata
    """
    metadata_lst = [
        URLMetadata(
            dataset_describe="1234",
            dataset_version="1.0.0",
            extractor_name="metalad_core",
            extractor_version="0.14.0",
            extraction_parameter=dict(a=1, b=2),
            extracted_metadata=dict(c=3, d=4),
            url_id=1,
        ),
        URLMetadata(
            dataset_describe="1234",
            dataset_version="1.0.0",
            extractor_name="metalad_studyminimet",
            extractor_version="0.1.0",
            extraction_parameter=dict(a=1, b=2),
            extracted_metadata=dict(c=3, d=4),
            url_id=1,
        ),
        URLMetadata(
            dataset_describe="1234",
            dataset_version="1.0.0",
            extractor_name="metalad_core",
            extractor_version="0.14.0",
            extraction_parameter=dict(a=1, b=2),
            extracted_metadata=dict(c=3, d=4),
            url_id=3,
        ),
    ]

    with flask_app.app_context():
        for metadata in metadata_lst:
            db.session.add(metadata)
        db.session.commit()
