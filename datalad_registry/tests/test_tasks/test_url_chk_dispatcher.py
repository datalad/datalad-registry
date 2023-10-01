import pytest

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
