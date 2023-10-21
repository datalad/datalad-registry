from datalad.distribution.dataset import require_dataset
import pytest

from datalad_registry.blueprints.api.url_metadata import URLMetadataModel
from datalad_registry.models import RepoUrl, URLMetadata, db
from datalad_registry.tasks import ExtractMetaStatus, extract_ds_meta
from datalad_registry.utils.datalad_tls import get_head_describe

from . import TEST_MIN_REPO_COMMIT_HEXSHA, TEST_MIN_REPO_TAG

_BASIC_EXTRACTOR = "metalad_core"


# Use fixture `flask_app` to ensure that the Celery app is initialized,
# and the db and the cache are clean
@pytest.mark.usefixtures("flask_app")
class TestExtractDsMeta:
    @pytest.mark.usefixtures("populate_db_with_unprocessed_dataset_urls")
    @pytest.mark.parametrize("url_id", [1, 7, 10])
    def test_nonexistent_ds_url(self, url_id):
        """
        Test the case that the given RepoUrl ID argument has no corresponding
        RepoUrl in the database
        """
        status = extract_ds_meta(url_id, _BASIC_EXTRACTOR)
        assert status is ExtractMetaStatus.NO_RECORD

    @pytest.mark.usefixtures("populate_db_with_unprocessed_dataset_urls")
    @pytest.mark.parametrize("url_id", [2, 3, 4, 5, 6])
    def test_unprocessed_ds_url(self, url_id):
        """
        Test the case that the specified RepoUrl, by ID, has not been processed
        """
        with pytest.raises(ValueError):
            extract_ds_meta(url_id, _BASIC_EXTRACTOR)

    @pytest.mark.usefixtures("populate_db_with_unprocessed_dataset_urls")
    @pytest.mark.parametrize("url_id", [2, 3, 4, 5, 6])
    def test_processed_ds_url_without_cache_path(self, url_id, flask_app):
        """
        Test the case that the specified RepoUrl, by ID, has been processed but
        has no cache path
        """
        with flask_app.app_context():
            url = db.session.execute(
                db.select(RepoUrl).where(RepoUrl.id == url_id)
            ).scalar_one()
            url.processed = True
            db.session.commit()

        with pytest.raises(AssertionError):
            extract_ds_meta(url_id, _BASIC_EXTRACTOR)

    def test_valid_ds_url_for_metadata_extraction(self, processed_ds_urls, flask_app):
        """
        Test the case that the specified RepoUrl, by ID, is valid for metadata
        extraction
        """
        for url_id in processed_ds_urls:
            extract_ds_meta(url_id, _BASIC_EXTRACTOR)

        with flask_app.app_context():
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

        assert (
            extract_ds_meta(test_repo_url_id, _BASIC_EXTRACTOR)
            is ExtractMetaStatus.SUCCEEDED
        )

        with flask_app.app_context():
            url = db.session.execute(
                db.select(RepoUrl).where(RepoUrl.id == test_repo_url_id)
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

    def test_aborted_due_to_missing_file(self, flask_app, processed_ds_urls):
        """
        Test that metadata extraction returns ExtractMetaStatus.ABORTED when
        some required file is missing for the given extractor
        """

        test_repo_url_id = processed_ds_urls[0]

        assert (
            extract_ds_meta(test_repo_url_id, "metalad_studyminimeta")
            is ExtractMetaStatus.ABORTED
        )

        with flask_app.app_context():
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

        # Extract metadata twice
        # The first one should result in a succeeded status
        # The second one should result in a skipped status
        assert (
            extract_ds_meta(test_repo_url_id, _BASIC_EXTRACTOR)
            is ExtractMetaStatus.SUCCEEDED
        )
        assert (
            extract_ds_meta(test_repo_url_id, _BASIC_EXTRACTOR)
            is ExtractMetaStatus.SKIPPED
        )

        with flask_app.app_context():
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
                flask_app.config["DATALAD_REGISTRY_DATASET_CACHE"]
                / db.session.execute(
                    db.select(RepoUrl.cache_path).where(RepoUrl.id == test_repo_url_id)
                ).scalar_one()
            )

        test_ds = require_dataset(test_repo_path, check_installed=True, purpose="test")

        # Set dataset one commit before the reference tag
        test_ds.repo.call_git(["checkout", f"{TEST_MIN_REPO_TAG}^"])

        # Extract metadata for the dataset at the older version
        assert (
            extract_ds_meta(test_repo_url_id, _BASIC_EXTRACTOR)
            is ExtractMetaStatus.SUCCEEDED
        )

        with flask_app.app_context():
            # There should be only one piece of metadata saved to database
            dated_metadata_ds_version = (
                db.session.execute(db.select(URLMetadata)).scalar_one().dataset_version
            )

        # Set dataset to the reference tag
        test_ds.repo.call_git(["checkout", TEST_MIN_REPO_TAG])

        # Extract metadata for the dataset at the new version
        assert (
            extract_ds_meta(test_repo_url_id, _BASIC_EXTRACTOR)
            is ExtractMetaStatus.SUCCEEDED
        )

        with flask_app.app_context():
            # There should be only one piece of metadata saved to database
            current_metadata = db.session.execute(db.select(URLMetadata)).scalar_one()

            assert current_metadata.dataset_version != dated_metadata_ds_version
            assert current_metadata.dataset_version == TEST_MIN_REPO_COMMIT_HEXSHA

    def test_builtin_extractor(self, dandi_repo_url_with_up_to_date_clone, flask_app):
        """
        Test the case that the given extractor is one of the built-in ones
        """
        repo_url = dandi_repo_url_with_up_to_date_clone[0]
        ds_clone = dandi_repo_url_with_up_to_date_clone[2]

        assert (
            extract_ds_meta(repo_url.id, "dandi:dandiset")
            is ExtractMetaStatus.SUCCEEDED
        )

        with flask_app.app_context():
            url_metadata = db.session.execute(db.select(URLMetadata)).scalar_one()

        assert url_metadata.dataset_describe == get_head_describe(ds_clone)
        assert url_metadata.dataset_version == ds_clone.repo.get_hexsha()
        assert url_metadata.extractor_name == "dandi:dandiset"
        assert url_metadata.extractor_version == "0.0.1"
        assert url_metadata.extraction_parameter == {}
        assert url_metadata.extracted_metadata == {"name": "test-dandi-ds"}
        assert url_metadata.url_id == repo_url.id
