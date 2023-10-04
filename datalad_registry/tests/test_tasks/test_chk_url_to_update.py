from datetime import datetime, timezone

import pytest

from datalad_registry.models import RepoUrl, db
from datalad_registry.tasks import ChkUrlStatus, chk_url_to_update

from . import FIXED_DATETIME_NOW_VALUE


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

    @pytest.mark.usefixtures("populate_with_dataset_urls", "fix_datetime_now")
    @pytest.mark.parametrize(
        "url_id, initial_last_chk_dt, original_n_failed_chks, original_chk_req_dt",
        [
            (
                1,
                datetime(2008, 7, 18, 19, 34, 34, tzinfo=timezone.utc),
                0,
                datetime(2008, 7, 18, 18, 34, 34, tzinfo=timezone.utc),
            ),
            (2, datetime(2009, 6, 18, 19, 34, 7, tzinfo=timezone.utc), 2, None),
            (
                3,
                datetime(2004, 6, 18, 18, 33, 7, tzinfo=timezone.utc),
                9,
                datetime(2004, 6, 19, 18, 34, 34, tzinfo=timezone.utc),
            ),
        ],
    )
    def test_update_ds_clone_failure(
        self,
        url_id,
        initial_last_chk_dt,
        original_n_failed_chks,
        original_chk_req_dt,
        monkeypatch,
        flask_app,
    ):
        """
        Test the case that updating the clone of the dataset in the local cache fails,
        i.e., the function `update_ds_clone` raises an exception
        """

        def mock_update_ds_clone(*_args, **_kwargs):
            raise RuntimeError("Mocked exception")

        from datalad_registry import tasks

        monkeypatch.setattr(tasks, "update_ds_clone", mock_update_ds_clone)

        with pytest.raises(RuntimeError, match="Mocked exception"):
            chk_url_to_update(url_id, initial_last_chk_dt)

        with flask_app.app_context():
            repo_url: RepoUrl = db.session.execute(
                db.select(RepoUrl).filter_by(id=url_id)
            ).scalar_one()

            # Verify that `n_failed_chks` and `last_chk_dt` of the `RepoUrl` records
            # identified by the given `url_id`s are updated
            assert repo_url.n_failed_chks == original_n_failed_chks + 1
            assert repo_url.last_chk_dt == FIXED_DATETIME_NOW_VALUE

            # Verify that `chk_req_dt` of the `RepoUrl` record identified by the given
            # `url_id` is not modified
            assert repo_url.chk_req_dt == original_chk_req_dt
