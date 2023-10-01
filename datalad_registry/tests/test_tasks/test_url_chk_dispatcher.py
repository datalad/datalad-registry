from datetime import datetime, timezone

import pytest

from datalad_registry.tasks import url_chk_dispatcher


@pytest.fixture
def set_datetime_now(monkeypatch):
    """
    Set the `datalad_registry.tasks.datetime.now()` to a fixed value
    """

    class MockDateTime:
        @classmethod
        def now(cls, *_args, **_kwargs):
            return datetime(2023, 9, 30, 19, 20, 34, tzinfo=timezone.utc)

    from datalad_registry import tasks

    monkeypatch.setattr(tasks, "datetime", MockDateTime)


# Use fixture `flask_app` to ensure that the Celery app is initialized,
# and the db and the cache are clean
@pytest.mark.usefixtures("flask_app")
class TestUrlChkDispatcher:
    def test_empty_db(self):
        """
        Test the case in which the database is empty
        """
        assert url_chk_dispatcher() == []
