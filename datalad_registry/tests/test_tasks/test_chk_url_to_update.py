from datetime import datetime, timezone
from pathlib import Path

import pytest

from datalad_registry.models import RepoUrl, db
from datalad_registry.tasks import ChkUrlStatus, chk_url_to_update

from . import FIXED_DATETIME_NOW_VALUE


# Use fixture `flask_app` to ensure that the Celery app is initialized,
# and the db and the cache are clean
@pytest.mark.usefixtures("flask_app")
class TestChkUrlToUpdate:
    @pytest.mark.usefixtures("populate_with_std_ds_urls")
    @pytest.mark.parametrize("invalid_url_id", [-1, 0, 5, 10])
    def test_repo_url_not_found(self, invalid_url_id):
        """
        Test the case that no RepoUrl record with the given ID exists in the database
        """
        assert chk_url_to_update(invalid_url_id, None) is ChkUrlStatus.ABORTED

    @pytest.mark.usefixtures("populate_with_std_ds_urls")
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

    @pytest.mark.usefixtures("populate_with_std_ds_urls", "fix_datetime_now")
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

    @pytest.mark.usefixtures("fix_datetime_now")
    @pytest.mark.parametrize(
        "repo_url_name, update_available, resulting_in_new_clone",
        [
            ("repo_url_with_up_to_date_clone", False, False),
            ("repo_url_outdated_by_new_file", True, False),
            ("repo_url_off_sync_by_new_default_branch", False, True),
        ],
    )
    def test_success_return(
        self,
        repo_url_name,
        update_available,
        resulting_in_new_clone,
        request,
        flask_app,
    ):
        """
        Test the case that the clone of the dataset in the local cache is up-to-date
        """
        repo_url: RepoUrl = request.getfixturevalue(repo_url_name)[0]
        original_cache_path = repo_url.cache_path

        # Set fields in `repo_url` that are related
        # to the operation of `chk_url_to_update`
        with flask_app.app_context():
            repo_url.n_failed_chks = 7
            repo_url.last_chk_dt = datetime(2023, 6, 18, 18, 33, 7, tzinfo=timezone.utc)
            repo_url.chk_req_dt = datetime(2023, 6, 17, 20, 33, 7, tzinfo=timezone.utc)

            db.session.add(repo_url)
            db.session.commit()
            db.session.refresh(repo_url)

        assert chk_url_to_update(repo_url.id, repo_url.last_chk_dt) is (
            ChkUrlStatus.OK_UPDATED if update_available else ChkUrlStatus.OK_CHK_ONLY
        )

        # Verify the state of the `repo_url` record after `chk_url_to_update`
        with flask_app.app_context():
            db.session.add(repo_url)
            db.session.refresh(repo_url)
        assert repo_url.n_failed_chks == 0
        assert repo_url.last_chk_dt == FIXED_DATETIME_NOW_VALUE
        assert repo_url.chk_req_dt is None

        if resulting_in_new_clone:
            assert repo_url.cache_path != original_cache_path

            # Verify that the old clone is removed
            assert not Path(original_cache_path).is_dir()
        else:
            assert repo_url.cache_path == original_cache_path

    @pytest.mark.usefixtures("fix_datetime_now")
    @pytest.mark.parametrize(
        "repo_url_name, resulting_in_new_clone",
        [
            ("repo_url_outdated_by_new_file", False),
            ("repo_url_outdated_by_new_file_at_new_default_branch", True),
        ],
    )
    def test_update_dataset_url_info_failure(
        self,
        repo_url_name,
        resulting_in_new_clone,
        request,
        monkeypatch,
        mocker,
        flask_app,
    ):
        """
        Test the case of failure in updating the dataset URL representation
        in the database, i.e., the call of `_update_dataset_url_info`
        raising an exception
        """
        from datalad_registry import tasks

        repo_url, remote_ds, old_clone = request.getfixturevalue(repo_url_name)

        with flask_app.app_context():
            original_n_failed_chks = repo_url.n_failed_chks
            original_chk_req_dt = repo_url.chk_req_dt
            original_cache_path_abs = repo_url.cache_path_abs
            original_head = repo_url.head

        update_ds_clone_spy = mocker.spy(tasks, "update_ds_clone")

        def mock_update_dataset_url_info(dataset_url: RepoUrl, *_args, **_kwargs):
            dataset_url.head = remote_ds.repo.get_hexsha()
            raise RuntimeError("Exception from `mock_update_dataset_url_info`")

        monkeypatch.setattr(
            tasks, "_update_dataset_url_info", mock_update_dataset_url_info
        )

        with pytest.raises(
            RuntimeError, match="Exception from `mock_update_dataset_url_info`"
        ):
            chk_url_to_update(repo_url.id, repo_url.last_chk_dt)

        # Verify the state of the `repo_url` record after `chk_url_to_update`
        with flask_app.app_context():
            db.session.add(repo_url)
            db.session.refresh(repo_url)

            # Verify that `n_failed_chks` and `last_chk_dt` of the `RepoUrl` records
            # are updated
            assert repo_url.n_failed_chks == original_n_failed_chks + 1
            assert repo_url.last_chk_dt == FIXED_DATETIME_NOW_VALUE

            # Verify that `chk_req_dt` of the `RepoUrl` record is not modified
            assert repo_url.chk_req_dt == original_chk_req_dt

            # Verify that `cache_path_abs` of the `RepoUrl` record is not modified
            assert repo_url.cache_path_abs == original_cache_path_abs

            # Verify that `head` of the `RepoUrl` record is not modified
            assert repo_url.head == original_head

        possible_new_clone, is_clone_new = update_ds_clone_spy.spy_return

        # Verify the state of the clone output by `update_ds_clone` is indeed what's
        # expected
        assert is_clone_new == resulting_in_new_clone

        if resulting_in_new_clone:
            # The new clone should be removed
            assert not possible_new_clone.pathobj.is_dir()
        else:
            # The old clone should have the same HEAD as before
            assert old_clone.repo.get_hexsha() == original_head

            # The old clone should not have updated to the remote dataset
            assert old_clone.repo.get_hexsha() != remote_ds.repo.get_hexsha()
