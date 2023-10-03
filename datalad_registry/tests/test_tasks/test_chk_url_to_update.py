import pytest

from datalad_registry.tasks import ChkUrlStatus, chk_url_to_update


# Use fixture `flask_app` to ensure that the Celery app is initialized,
# and the db and the cache are clean
@pytest.mark.usefixtures("flask_app")
class TestChkUrlToUpdate:
    @pytest.mark.usefixtures("populate_with_dataset_urls")
    @pytest.mark.parametrize("invalid_url_id", [-1, 0, 5, 10])
    def test_repo_url_not_found(self, invalid_url_id):
        """
        Test the case that no RepoUrl record with the given ID exists in the database
        """
        assert chk_url_to_update(invalid_url_id, None) is ChkUrlStatus.ABORTED
