from datetime import datetime, timezone

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

    @pytest.mark.usefixtures("populate_with_dataset_urls")
    @pytest.mark.parametrize(
        "url_id, initial_last_chk_dt",
        [
            (1, None),
            (2, datetime(2009, 6, 18, 18, 34, 31, tzinfo=timezone.utc)),
            (3, datetime(2004, 6, 18, 19, 33, 7, tzinfo=timezone.utc)),
        ],
    )
    def test_chk_handled_by_another_process(self, url_id, initial_last_chk_dt):
        """
        Test the case that the check to update the dataset at the given URL is
        already handled by another process (signaled by having a modified `last_chk_dt`
        in the `RepoUrl` record)
        """
        assert chk_url_to_update(url_id, initial_last_chk_dt) is ChkUrlStatus.SKIPPED
