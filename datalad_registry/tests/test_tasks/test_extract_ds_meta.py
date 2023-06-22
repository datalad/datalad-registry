from pathlib import Path

from datalad.distribution.dataset import require_dataset
import pytest

from datalad_registry.blueprints.api.url_metadata import URLMetadataModel
from datalad_registry.models import URL, URLMetadata, db
from datalad_registry.tasks import ExtractMetaStatus, extract_ds_meta

from . import TEST_MIN_REPO_COMMIT_HEXSHA, TEST_MIN_REPO_TAG

_BASIC_EXTRACTOR = "metalad_core"


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

    def test_succeeded(self, flask_app, processed_ds_urls):
        """
        Test that metadata extraction returns ExtractMetaStatus.SUCCEEDED when
        all provided arguments are valid, and the given extractor doesn't require
        any special file to be present in the dataset
        """

        test_repo_url_id = processed_ds_urls[0]

        with flask_app.app_context():
            ret = extract_ds_meta(test_repo_url_id, _BASIC_EXTRACTOR)

            assert ret == ExtractMetaStatus.SUCCEEDED

            url = db.session.execute(
                db.select(URL).where(URL.id == test_repo_url_id)
            ).scalar_one()

            metadata_lst = url.metadata_

            # Verify the number of pieces of metadata
            assert len(metadata_lst) == 1

            metadata = URLMetadataModel.from_orm(metadata_lst[0])

            # Verify metadata saved to database
            assert metadata.dataset_describe == TEST_MIN_REPO_TAG
            assert metadata.dataset_version == TEST_MIN_REPO_COMMIT_HEXSHA
            assert metadata.extractor_name == _BASIC_EXTRACTOR
            assert metadata.extraction_parameter == {}
            # noinspection HttpUrlsUsage
            assert metadata.extracted_metadata["@context"] == {
                "@vocab": "http://schema.org/",
                "datalad": "http://dx.datalad.org/",
            }

    def test_aborted(self, flask_app, processed_ds_urls):
        """
        Test that metadata extraction returns ExtractMetaStatus.ABORTED when
        some required file is missing for the given extractor
        """

        test_repo_url_id = processed_ds_urls[0]

        with flask_app.app_context():
            ret = extract_ds_meta(test_repo_url_id, "metalad_studyminimeta")
            assert ret == ExtractMetaStatus.ABORTED

            # Ensure no metadata was saved to database
            metadata = db.session.execute(db.select(URLMetadata)).all()
            assert len(metadata) == 0

    def test_skipped(self, flask_app, processed_ds_urls):
        """
        Test that metadata extraction returns ExtractMetaStatus.SKIPPED when
        metadata for the given extractor has already been extracted for the
        given dataset of the given version
        """

        test_repo_url_id = processed_ds_urls[0]

        with flask_app.app_context():
            # Extract metadata twice
            # The second one should result in a skipped status
            extract_ds_meta(test_repo_url_id, _BASIC_EXTRACTOR)
            ret = extract_ds_meta(test_repo_url_id, _BASIC_EXTRACTOR)
            assert ret == ExtractMetaStatus.SKIPPED

            # Ensure there is only one piece of metadata saved to database
            metadata = db.session.execute(db.select(URLMetadata)).all()
            assert len(metadata) == 1

    def test_new_dataset_version(self, flask_app, processed_ds_urls):
        """
        Test extraction of metadata for a dataset at a new version after the extraction
        of metadata for the same dataset at an older version

        The extraction should return ExtractMetaStatus.SUCCEEDED, and there should be
        only one piece of metadata saved to database, the latest one
        """

        test_repo_url_id = processed_ds_urls[0]

        # Fetch test repo cache path
        with flask_app.app_context():
            test_repo_path = str(
                Path(flask_app.config["DATALAD_REGISTRY_DATASET_CACHE"])
                / db.session.execute(
                    db.select(URL.cache_path).where(URL.id == test_repo_url_id)
                ).scalar_one()
            )

        test_ds = require_dataset(test_repo_path, check_installed=True, purpose="test")

        # Set dataset one commit before the reference tag for test
        test_ds.repo.call_git(["checkout", f"{TEST_MIN_REPO_TAG}^"])

        with flask_app.app_context():
            # Extract metadata for the dataset at the older version
            ret = extract_ds_meta(test_repo_url_id, _BASIC_EXTRACTOR)
            assert ret == ExtractMetaStatus.SUCCEEDED

            # There should be only one piece of metadata saved to database
            dated_metadata = db.session.execute(db.select(URLMetadata)).scalar_one()

            # Set dataset to the reference tag for test
            test_ds.repo.call_git(["checkout", TEST_MIN_REPO_TAG])

            # Extract metadata for the dataset at the new version
            ret = extract_ds_meta(test_repo_url_id, _BASIC_EXTRACTOR)
            assert ret == ExtractMetaStatus.SUCCEEDED

            # There should be only one piece of metadata saved to database
            current_metadata = db.session.execute(db.select(URLMetadata)).scalar_one()

            assert current_metadata.dataset_version != dated_metadata.dataset_version
            assert current_metadata.dataset_version == TEST_MIN_REPO_COMMIT_HEXSHA
