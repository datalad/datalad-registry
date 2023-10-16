from pathlib import Path

from flask import current_app
import pytest
from sqlalchemy import select

from datalad_registry.models import RepoUrl, db


class TestRepoUrl:
    @pytest.mark.parametrize(
        "cache_path", [None, "a/b/c", "c/b/a", "72e/cd9/cc10534e2a9f551e32119e0e60"]
    )
    def test_cache_path_absolute(self, cache_path, flask_app):
        """
        Test that the cache path of a RepoUrl is the string representation of the
        last three components of the path if the path is absolute.
        """
        url = "https://www.example.com"
        with flask_app.app_context():
            repo_url = RepoUrl(url=url, cache_path=cache_path)
            db.session.add(repo_url)
            db.session.commit()

            repo_url = (
                db.session.execute(select(RepoUrl).filter_by(url=url)).scalars().one()
            )

            base_cache_path = current_app.config["DATALAD_REGISTRY_DATASET_CACHE"]

            assert isinstance(base_cache_path, Path)

            if cache_path is None:
                assert repo_url.cache_path_abs is None
            else:
                assert (
                    repo_url.cache_path_abs
                    == current_app.config["DATALAD_REGISTRY_DATASET_CACHE"] / cache_path
                )
