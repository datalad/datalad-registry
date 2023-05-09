import pytest

from datalad_registry.models import URL, URLMetadata, db
from datalad_registry.tasks import extract_ds_meta, process_dataset_url

from . import TEST_MIN_REPO_URL

_BASIC_EXTRACTOR = "metalad_core"


@pytest.fixture
def processed_ds_urls(flask_app, two_files_ds_annex) -> list[int]:
    """
    Add valid dataset URLs to the database, process them, and return their IDs,
    the primary keys
    """

    urls = [URL(url=TEST_MIN_REPO_URL), URL(url=two_files_ds_annex.path)]

    with flask_app.app_context():
        for url in urls:
            db.session.add(url)
        db.session.commit()

        for url in urls:
            process_dataset_url(url.id)

        return [url.id for url in urls]


class TestExtractDsMeta:
    @pytest.mark.usefixtures("populate_db_with_unprocessed_dataset_urls")
    @pytest.mark.parametrize("url_id", [1, 7, 10])
    def test_nonexistent_ds_url(self, url_id, flask_app):
        """
        Test the case that the given dataset URL ID argument has no corresponding
        dataset URL in the database
        """
        with flask_app.app_context():
            with pytest.raises(ValueError):
                extract_ds_meta(url_id, _BASIC_EXTRACTOR)

    @pytest.mark.usefixtures("populate_db_with_unprocessed_dataset_urls")
    @pytest.mark.parametrize("url_id", [2, 3, 4, 5, 6])
    def test_unprocessed_ds_url(self, url_id, flask_app):
        """
        Test the case that the specified dataset URL, by ID, has not been processed
        """
        with flask_app.app_context():
            with pytest.raises(ValueError):
                extract_ds_meta(url_id, _BASIC_EXTRACTOR)

    @pytest.mark.usefixtures("populate_db_with_unprocessed_dataset_urls")
    @pytest.mark.parametrize("url_id", [2, 3, 4, 5, 6])
    def test_processed_ds_url_without_cache_path(self, url_id, flask_app):
        """
        Test the case that the specified dataset URL, by ID, has been processed but
        has no cache path
        """
        with flask_app.app_context():
            url = db.session.execute(
                db.select(URL).where(URL.id == url_id)
            ).scalar_one()
            url.processed = True

            with pytest.raises(AssertionError):
                extract_ds_meta(url_id, _BASIC_EXTRACTOR)

    def test_valid_ds_url_for_metadata_extraction(self, processed_ds_urls, flask_app):
        """
        Test the case that the specified dataset URL, by ID, is valid for metadata
        extraction
        """

        with flask_app.app_context():
            for url_id in processed_ds_urls:
                extract_ds_meta(url_id, _BASIC_EXTRACTOR)

            # Confirm that the dataset URLs metadata have been extracted
            for url_id in processed_ds_urls:
                res = db.session.execute(
                    db.select(URLMetadata.extractor_name).filter_by(url_id=url_id)
                ).all()

                assert len(res) == 1
                assert res[0][0] == _BASIC_EXTRACTOR
