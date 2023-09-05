# This file defines tests for various helpers in `datalad_registry.tasks`

import pytest

from datalad_registry.models import RepoUrl, db
from datalad_registry.tasks import _iter_url_ids


@pytest.fixture
def ten_repo_urls(flask_app):
    """
    The fixture of a list of 10 RepoUrl objects
    """
    with flask_app.app_context():
        urls = [RepoUrl(url=f"https://example.com/{i}") for i in range(10)]
        for url in urls:
            db.session.add(url)
        db.session.commit()

        # By yielding instead of returning,
        # a user of this fixture is automatically put in the app context
        yield urls


class TestIterUrlIds:
    @pytest.mark.parametrize("invalid_limit", [-1, -2, -50, -100])
    def test_invalid_limit(self, invalid_limit):
        """
        Test the case that the given limit is invalid, negative
        """
        with pytest.raises(ValueError, match="`limit` must be non-negative"):
            next(_iter_url_ids([], invalid_limit))

    @pytest.mark.parametrize("limit", [0, 4, 6, 8, 9])
    def test_limit_by_limit(self, limit, ten_repo_urls):
        """
        Test the case that the results of the iterations are limited by the value
        of the `limit` parameter
        """
        iterated_url_ids = list(_iter_url_ids(ten_repo_urls, limit))
        assert iterated_url_ids == list(range(1, 1 + limit))

    @pytest.mark.parametrize("limit", [10, 11, 20, 41])
    def test_limit_by_length(self, limit, ten_repo_urls):
        """
        Test the case that the results of the iterations are limited by the number
        of elements in the iterable
        """
        iterated_url_ids = list(_iter_url_ids(ten_repo_urls, limit))
        assert iterated_url_ids == list(range(1, 1 + len(ten_repo_urls)))
