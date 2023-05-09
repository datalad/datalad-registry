import pytest

from datalad_registry.models import URL, db

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
        non_dataset_url = URL(url="https://www.datalad.org/")
        db.session.add(non_dataset_url)  # id == 1

        db.session.add(URL(url=TEST_MIN_REPO_URL))  # id == 2
        db.session.add(URL(url=empty_ds_annex.path))  # id == 3
        db.session.add(URL(url=empty_ds_non_annex.path))  # id == 4
        db.session.add(URL(url=two_files_ds_annex.path))  # id == 5
        db.session.add(URL(url=two_files_ds_non_annex.path))  # id == 6

        db.session.commit()

        db.session.delete(non_dataset_url)
        db.session.commit()  # 1 is no longer a valid dataset URL id
