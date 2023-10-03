from datetime import datetime, timezone

import pytest

from datalad_registry.models import RepoUrl, db
from datalad_registry.tasks import process_dataset_url

from . import TEST_MIN_REPO_URL


@pytest.fixture
def populate_db_with_unprocessed_dataset_urls(
    flask_app,
    empty_ds_annex,
    empty_ds_non_annex,
    two_files_ds_annex,
    two_files_ds_non_annex,
):
    """
    Populate the database with unprocessed dataset URLs
    """

    with flask_app.app_context():
        non_dataset_url = RepoUrl(url="https://www.datalad.org/")
        db.session.add(non_dataset_url)  # id == 1

        db.session.add(RepoUrl(url=TEST_MIN_REPO_URL))  # id == 2
        db.session.add(RepoUrl(url=empty_ds_annex.path))  # id == 3
        db.session.add(RepoUrl(url=empty_ds_non_annex.path))  # id == 4
        db.session.add(RepoUrl(url=two_files_ds_annex.path))  # id == 5
        db.session.add(RepoUrl(url=two_files_ds_non_annex.path))  # id == 6

        db.session.commit()

        db.session.delete(non_dataset_url)
        db.session.commit()  # 1 is no longer a valid RepoUrl id


@pytest.fixture
def processed_ds_urls(flask_app, two_files_ds_annex) -> list[int]:
    """
    Add valid dataset URLs to the database, process them, and return their IDs,
    the primary keys
    """

    urls = [RepoUrl(url=TEST_MIN_REPO_URL), RepoUrl(url=two_files_ds_annex.path)]

    with flask_app.app_context():
        for url in urls:
            db.session.add(url)
        db.session.commit()

        url_ids = [url.id for url in urls]

    for url_id in url_ids:
        process_dataset_url(url_id)

    return url_ids


@pytest.fixture
def fix_datetime_now(monkeypatch):
    """
    Fix the `datalad_registry.tasks.datetime.now()` to return a specific value
    """

    class MockDateTime(datetime):
        @classmethod
        def now(cls, *_args, **_kwargs):
            return datetime(2023, 9, 30, 19, 20, 34, tzinfo=timezone.utc)

    from datalad_registry import tasks

    monkeypatch.setattr(tasks, "datetime", MockDateTime)
