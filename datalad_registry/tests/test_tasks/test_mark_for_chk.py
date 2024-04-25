from datetime import datetime, timezone

import pytest
from pytest_mock import MockerFixture

from datalad_registry.models import RepoUrl, db
from datalad_registry.tasks import mark_for_chk


# Use fixture `flask_app` to ensure that the Celery app is initialized,
# and the db and the cache are clean
@pytest.mark.usefixtures("flask_app")
class TestMarkForChk:
    @pytest.mark.usefixtures("populate_with_std_ds_urls")
    @pytest.mark.parametrize("url_id", [5, 42])
    def test_non_existing_url(self, url_id, mocker: MockerFixture):
        """
        Test the case that the given RepoUrl ID argument has no corresponding
        RepoUrl record in the database
        """

        class MockDateTime:
            @classmethod
            def now(cls, *args, **kwargs):
                return datetime.now(*args, **kwargs)

        datetime_mock = mocker.Mock(wraps=MockDateTime)

        mocker.patch("datalad_registry.tasks.datetime", new=datetime_mock)

        mark_for_chk(url_id)

        datetime_mock.now.assert_not_called()

    @pytest.mark.usefixtures("populate_with_std_ds_urls")
    @pytest.mark.parametrize(
        "url_id, original_chk_req_dt, expecting_chk_req_dt_changed",
        [
            (
                1,
                datetime(2008, 7, 18, 18, 34, 34, tzinfo=timezone.utc),
                False,
            ),
            (2, None, True),
            (
                3,
                datetime(2004, 6, 19, 18, 34, 34, tzinfo=timezone.utc),
                False,
            ),
            (4, None, False),
        ],
    )
    def test_existing_url(
        self, url_id, original_chk_req_dt, expecting_chk_req_dt_changed, flask_app
    ):
        mark_for_chk(url_id)

        # Verify the representation of the URL in the DB
        with flask_app.app_context():
            repo_url: RepoUrl = db.session.execute(
                db.select(RepoUrl).filter_by(id=url_id)
            ).scalar_one()

            if expecting_chk_req_dt_changed:
                if original_chk_req_dt is None:
                    assert isinstance(repo_url.chk_req_dt, datetime)
                else:
                    raise ValueError("This should not happen")
            else:
                if original_chk_req_dt is None:
                    assert repo_url.chk_req_dt is None
                else:
                    assert repo_url.chk_req_dt == original_chk_req_dt
