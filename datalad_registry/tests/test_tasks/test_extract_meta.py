from datalad import api as dl
from datalad.distribution.dataset import require_dataset
import pytest

from datalad_registry.tasks import ExtractMetaStatus, extract_meta

_TEST_REPO_URL = "https://github.com/datalad/testrepo--minimalds.git"
_TEST_REPO_TAG = "0.1.0"
_TEST_REPO_COMMIT_HEXSHA = "ac9ba85cf1e8a004e7c24ebb6b5cd861d53e3998"
_BASIC_EXTRACTOR = "metalad_core"


@pytest.fixture
def test_repo_url_id(flask_app) -> int:
    from datalad_registry.models import URL, db

    url = URL(url=_TEST_REPO_URL, head_describe=_TEST_REPO_TAG)

    with flask_app.app_context():
        db.session.add(url)
        db.session.commit()
        return url.id


@pytest.fixture(scope="session")
def test_repo_path(tmp_path_factory):
    test_repo_path_ = tmp_path_factory.mktemp("test_repo")
    dl.clone(
        _TEST_REPO_URL,
        path=test_repo_path_,
        git_clone_opts=[f"--branch={_TEST_REPO_TAG}"],
    )
    return test_repo_path_


class TestExtractMeta:
    def test_skipped(self, flask_app, test_repo_url_id, test_repo_path):
        """
        Test that metadata extraction returns ExtractMetaStatus.SKIPPED when
        metadata for the given extractor has already been extracted for the
        given dataset of the given version
        """
        from datalad_registry.models import URLMetadata, db

        with flask_app.app_context():
            # Extract metadata twice
            # The second one should result in a skipped status
            extract_meta(test_repo_url_id, test_repo_path, _BASIC_EXTRACTOR)
            ret = extract_meta(test_repo_url_id, test_repo_path, _BASIC_EXTRACTOR)
            assert ret == ExtractMetaStatus.SKIPPED

            # Ensure there is only one piece of metadata saved to database
            metadata = db.session.execute(db.select(URLMetadata)).all()
            assert len(metadata) == 1

    def test_new_dataset_version(self, flask_app, test_repo_url_id, test_repo_path):
        """
        Test extraction of metadata for a dataset at a new version after the extraction
        of metadata for the same dataset at an older version

        The extraction should return ExtractMetaStatus.SUCCEEDED, and there should be
        only one piece of metadata saved to database, the latest one
        """
        from datalad_registry.models import URLMetadata, db

        test_ds = require_dataset(test_repo_path, check_installed=True, purpose="test")

        # Set dataset one commit before the reference tag for test
        test_ds.repo.call_git(["checkout", f"{_TEST_REPO_TAG}^"])

        with flask_app.app_context():
            # Extract metadata for the dataset at the older version
            ret = extract_meta(test_repo_url_id, test_repo_path, _BASIC_EXTRACTOR)
            assert ret == ExtractMetaStatus.SUCCEEDED

            # There should be only one piece of metadata saved to database
            dated_metadata = db.session.execute(db.select(URLMetadata)).scalar_one()

            # Set dataset to the reference tag for test
            test_ds.repo.call_git(["checkout", _TEST_REPO_TAG])

            # Extract metadata for the dataset at the new version
            ret = extract_meta(test_repo_url_id, test_repo_path, _BASIC_EXTRACTOR)
            assert ret == ExtractMetaStatus.SUCCEEDED

            # There should be only one piece of metadata saved to database
            current_metadata = db.session.execute(db.select(URLMetadata)).scalar_one()

            assert current_metadata.dataset_version != dated_metadata.dataset_version
            assert current_metadata.dataset_version == _TEST_REPO_COMMIT_HEXSHA
