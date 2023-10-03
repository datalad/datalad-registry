from datetime import datetime, timezone

import pytest

from datalad_registry.models import RepoUrl, db
from datalad_registry.tasks import url_chk_dispatcher


# Use fixture `flask_app` to ensure that the Celery app is initialized,
# and the db and the cache are clean
@pytest.mark.usefixtures("flask_app")
class TestUrlChkDispatcher:
    def test_empty_db(self):
        """
        Test the case in which the database is empty
        """
        assert url_chk_dispatcher() == []

    @pytest.mark.usefixtures("fix_datetime_now")
    @pytest.mark.parametrize(
        "urls_in_db, expected_result",
        [
            # Test unqualified by not having processed
            (
                [
                    RepoUrl(
                        url="https://example.com/1",
                        last_update_dt=datetime(
                            2023, 9, 30, 17, 20, 34, tzinfo=timezone.utc
                        ),
                        last_chk_dt=None,
                        chk_req_dt=None,
                        n_failed_chks=0,
                        processed=True,
                    ),
                    RepoUrl(
                        url="https://example.com/2",
                        last_update_dt=datetime(
                            2023, 9, 30, 17, 20, 34, tzinfo=timezone.utc
                        ),
                        last_chk_dt=None,
                        chk_req_dt=None,
                        n_failed_chks=0,
                        processed=False,
                    ),
                ],
                [1],
            ),
            # Test unqualified by having failed too many times
            (
                [
                    RepoUrl(
                        url="https://example.com/1",
                        last_update_dt=datetime(
                            2023, 9, 30, 17, 20, 34, tzinfo=timezone.utc
                        ),
                        last_chk_dt=None,
                        chk_req_dt=None,
                        n_failed_chks=10,
                        processed=True,
                    ),
                    RepoUrl(
                        url="https://example.com/2",
                        last_update_dt=datetime(
                            2023, 9, 30, 17, 20, 34, tzinfo=timezone.utc
                        ),
                        last_chk_dt=None,
                        chk_req_dt=None,
                        n_failed_chks=0,
                        processed=True,
                    ),
                ],
                [2],
            ),
            # Test unqualified by updated too recently and qualified by
            # yet-to-be-checked check request
            (
                [
                    RepoUrl(
                        url="https://example.com/1",
                        last_update_dt=datetime(
                            2023, 9, 30, 19, 10, 34, tzinfo=timezone.utc
                        ),
                        last_chk_dt=datetime(
                            2023, 9, 30, 19, 15, 33, tzinfo=timezone.utc
                        ),
                        chk_req_dt=datetime(
                            2023, 9, 30, 19, 15, 34, tzinfo=timezone.utc
                        ),
                        n_failed_chks=0,
                        processed=True,
                    ),
                    RepoUrl(
                        url="https://example.com/2",
                        last_update_dt=datetime(
                            2023, 9, 30, 19, 10, 34, tzinfo=timezone.utc
                        ),
                        last_chk_dt=None,
                        chk_req_dt=datetime(
                            2023, 9, 30, 19, 15, 34, tzinfo=timezone.utc
                        ),
                        n_failed_chks=0,
                        processed=True,
                    ),
                    RepoUrl(
                        url="https://example.com/3",
                        last_update_dt=datetime(
                            2023, 9, 30, 19, 10, 34, tzinfo=timezone.utc
                        ),
                        last_chk_dt=None,
                        chk_req_dt=None,
                        n_failed_chks=0,
                        processed=True,
                    ),
                ],
                [1, 2],
            ),
            # Test qualified by handled requested check that has not been handled
            # for long enough
            (
                [
                    # This one is not qualified because the last check datetime is
                    # too recent
                    RepoUrl(
                        url="https://example.com/1",
                        last_update_dt=datetime(
                            2023, 9, 30, 12, 20, 34, tzinfo=timezone.utc
                        ),
                        last_chk_dt=datetime(
                            2023, 9, 30, 19, 1, 34, tzinfo=timezone.utc
                        ),
                        chk_req_dt=datetime(
                            2023, 9, 30, 15, 20, 34, tzinfo=timezone.utc
                        ),
                        n_failed_chks=3,
                        processed=True,
                    ),
                    # This one is qualified because the last check datetime is not
                    # too recent
                    RepoUrl(
                        url="https://example.com/2",
                        last_update_dt=datetime(
                            2023, 9, 30, 12, 20, 34, tzinfo=timezone.utc
                        ),
                        last_chk_dt=datetime(
                            2023, 9, 30, 18, 1, 34, tzinfo=timezone.utc
                        ),
                        chk_req_dt=datetime(
                            2023, 9, 30, 15, 20, 34, tzinfo=timezone.utc
                        ),
                        n_failed_chks=3,
                        processed=True,
                    ),
                ],
                [2],
            ),
            # Test sorting by category
            (
                [
                    # Not requested but qualified by last update datetime
                    # (This should be the 4th in the returned list because of the
                    # category it belongs to and its last update datetime)
                    RepoUrl(
                        url="https://example.com/1",
                        last_update_dt=datetime(
                            2023, 9, 30, 18, 20, 34, tzinfo=timezone.utc
                        ),
                        last_chk_dt=None,
                        chk_req_dt=None,
                        n_failed_chks=0,
                        processed=True,
                    ),
                    # Not requested but qualified by last check datetime
                    # (This should be the 3rd in the returned list because of the
                    # category it belongs to and its last check datetime)
                    RepoUrl(
                        url="https://example.com/2",
                        last_update_dt=datetime(
                            2023, 9, 30, 17, 20, 34, tzinfo=timezone.utc
                        ),
                        last_chk_dt=datetime(
                            2023, 9, 30, 17, 50, 34, tzinfo=timezone.utc
                        ),
                        chk_req_dt=None,
                        n_failed_chks=0,
                        processed=True,
                    ),
                    # Unhandled requested
                    # (This should be the 1st in the returned list)
                    RepoUrl(
                        url="https://example.com/3",
                        last_update_dt=datetime(
                            2023, 9, 30, 18, 50, 34, tzinfo=timezone.utc
                        ),
                        last_chk_dt=None,
                        chk_req_dt=datetime(
                            2023, 9, 30, 18, 40, 34, tzinfo=timezone.utc
                        ),
                        n_failed_chks=0,
                        processed=True,
                    ),
                    # Handled requested but handled too recently (not qualified)
                    # (This should not be returned)
                    RepoUrl(
                        url="https://example.com/4",
                        last_update_dt=datetime(
                            2023, 9, 30, 18, 20, 34, tzinfo=timezone.utc
                        ),
                        last_chk_dt=datetime(
                            2023, 9, 30, 19, 2, 34, tzinfo=timezone.utc
                        ),
                        chk_req_dt=datetime(
                            2023, 9, 30, 18, 55, 34, tzinfo=timezone.utc
                        ),
                        n_failed_chks=0,
                        processed=True,
                    ),
                    # Handled requested but not handled for long enough
                    # (This should be the 2nd in the returned list)
                    RepoUrl(
                        url="https://example.com/5",
                        last_update_dt=datetime(
                            2023, 9, 30, 17, 20, 34, tzinfo=timezone.utc
                        ),
                        last_chk_dt=datetime(
                            2023, 9, 30, 18, 2, 34, tzinfo=timezone.utc
                        ),
                        chk_req_dt=datetime(
                            2023, 9, 30, 17, 55, 34, tzinfo=timezone.utc
                        ),
                        n_failed_chks=5,
                        processed=True,
                    ),
                ],
                [3, 5, 2, 1],
            ),
            # Test sorting within the unhandled requested category
            # (The sorting should be done by check request datetime)
            (
                [
                    RepoUrl(
                        url="https://example.com/1",
                        last_update_dt=datetime(
                            2023, 9, 30, 18, 20, 34, tzinfo=timezone.utc
                        ),
                        last_chk_dt=None,
                        chk_req_dt=datetime(
                            2023, 9, 30, 18, 45, 34, tzinfo=timezone.utc
                        ),
                        n_failed_chks=0,
                        processed=True,
                    ),
                    RepoUrl(
                        url="https://example.com/2",
                        last_update_dt=datetime(
                            2023, 9, 30, 17, 20, 34, tzinfo=timezone.utc
                        ),
                        last_chk_dt=datetime(
                            2023, 9, 30, 18, 50, 33, tzinfo=timezone.utc
                        ),
                        chk_req_dt=datetime(
                            2023, 9, 30, 18, 50, 34, tzinfo=timezone.utc
                        ),
                        n_failed_chks=0,
                        processed=True,
                    ),
                ],
                [1, 2],
            ),
            # Test sorting within the handled requested category
            # (The sorting should be done by last check datetime)
            (
                [
                    RepoUrl(
                        url="https://example.com/1",
                        last_update_dt=datetime(
                            2023, 9, 30, 17, 20, 34, tzinfo=timezone.utc
                        ),
                        last_chk_dt=datetime(
                            2023, 9, 30, 17, 45, 34, tzinfo=timezone.utc
                        ),
                        chk_req_dt=datetime(
                            2023, 9, 30, 17, 40, 34, tzinfo=timezone.utc
                        ),
                        n_failed_chks=4,
                        processed=True,
                    ),
                    RepoUrl(
                        url="https://example.com/2",
                        last_update_dt=datetime(
                            2023, 9, 30, 17, 22, 34, tzinfo=timezone.utc
                        ),
                        last_chk_dt=datetime(
                            2023, 9, 30, 17, 44, 34, tzinfo=timezone.utc
                        ),
                        chk_req_dt=datetime(
                            2023, 9, 30, 17, 42, 34, tzinfo=timezone.utc
                        ),
                        n_failed_chks=4,
                        processed=True,
                    ),
                ],
                [2, 1],
            ),
            # Test not requested but qualified by last update or check being old enough
            # sorted by last update datetime or last check datetime
            # with the latter having higher priority
            (
                [
                    RepoUrl(
                        url="https://example.com/1",
                        last_update_dt=datetime(
                            2023, 9, 30, 17, 10, 34, tzinfo=timezone.utc
                        ),
                        last_chk_dt=datetime(
                            2023, 9, 30, 17, 25, 34, tzinfo=timezone.utc
                        ),
                        chk_req_dt=None,
                        n_failed_chks=0,
                        processed=True,
                    ),
                    RepoUrl(
                        url="https://example.com/2",
                        last_update_dt=datetime(
                            2023, 9, 30, 17, 20, 34, tzinfo=timezone.utc
                        ),
                        last_chk_dt=None,
                        chk_req_dt=None,
                        n_failed_chks=0,
                        processed=True,
                    ),
                ],
                [2, 1],
            ),
        ],
    )
    def test_non_empty_db(self, urls_in_db, expected_result, flask_app):
        """
        Test the case in which the database is not empty
        """
        # Set up the database with the given URLs
        with flask_app.app_context():
            db.session.add_all(urls_in_db)
            db.session.commit()

        assert url_chk_dispatcher() == expected_result
