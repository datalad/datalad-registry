from datetime import datetime
from pathlib import Path

from datalad.api import Dataset
from flask import Flask
import pytest

from datalad_registry.models import RepoUrl, db
from datalad_registry.tasks import process_dataset_url
from datalad_registry.tasks.utils import allocate_ds_path
from datalad_registry.utils.datalad_tls import clone

from . import FIXED_DATETIME_NOW_VALUE, TEST_MIN_REPO_URL


@pytest.fixture
def populate_db_with_unprocessed_dataset_urls(
    flask_app,
    empty_ds_annex,
    empty_ds_non_annex,
    two_files_ds_annex,
    two_files_ds_non_annex,
):
    """
    Populate the database with unprocessed dataset URLs
    """

    with flask_app.app_context():
        non_dataset_url = RepoUrl(url="https://www.datalad.org/")
        db.session.add(non_dataset_url)  # id == 1

        db.session.add(RepoUrl(url=TEST_MIN_REPO_URL))  # id == 2
        db.session.add(RepoUrl(url=empty_ds_annex.path))  # id == 3
        db.session.add(RepoUrl(url=empty_ds_non_annex.path))  # id == 4
        db.session.add(RepoUrl(url=two_files_ds_annex.path))  # id == 5
        db.session.add(RepoUrl(url=two_files_ds_non_annex.path))  # id == 6

        db.session.commit()

        db.session.delete(non_dataset_url)
        db.session.commit()  # 1 is no longer a valid RepoUrl id


@pytest.fixture
def processed_ds_urls(flask_app, two_files_ds_annex) -> list[int]:
    """
    Add valid dataset URLs to the database, process them, and return their IDs,
    the primary keys
    """

    urls = [RepoUrl(url=TEST_MIN_REPO_URL), RepoUrl(url=two_files_ds_annex.path)]

    with flask_app.app_context():
        for url in urls:
            db.session.add(url)
        db.session.commit()

        url_ids = [url.id for url in urls]

    for url_id in url_ids:
        process_dataset_url(url_id)

    return url_ids


@pytest.fixture
def fix_datetime_now(monkeypatch):
    """
    Fix the `datalad_registry.tasks.datetime.now()` to return a specific value
    """

    class MockDateTime(datetime):
        @classmethod
        def now(cls, *_args, **_kwargs):
            return FIXED_DATETIME_NOW_VALUE

    from datalad_registry import tasks

    monkeypatch.setattr(tasks, "datetime", MockDateTime)


def _establish_repo_url_with_up_to_date_clone(
    remote_repo: Dataset, base_cache_path: Path, flask_app: Flask
) -> tuple[RepoUrl, Dataset]:
    """
    Establish a `RepoUrl` object/record in the database with a corresponding clone
    of the remote repository at the local cache

    :param remote_repo: The remote repository to be cloned
    :param base_cache_path: The base path of the local cache
    :param flask_app: The Flask app
    :return: A tuple of the following
        - A `RepoUrl` object that represents the URL of a remote repository
          in the database
        - A `Dataset` object that represents a clone of the remote repository
          at the local cache
    """
    with flask_app.app_context():
        clone_path_relative = allocate_ds_path()
        clone_path_abs = base_cache_path / clone_path_relative

        ds_clone = clone(
            source=remote_repo,
            path=clone_path_abs,
            on_failure="stop",
            result_renderer="disabled",
        )

        # Add representation of the URL to the database
        url = RepoUrl(
            url=remote_repo.path,
            head=remote_repo.repo.get_hexsha(),
            processed=True,
            cache_path=str(clone_path_relative),
        )
        db.session.add(url)
        db.session.commit()

        # Reload the `url` object from the database
        db.session.refresh(url)

        return url, ds_clone


@pytest.fixture
def repo_url_with_up_to_date_clone(
    two_files_ds_annex_func_scoped, base_cache_path, flask_app
) -> tuple[RepoUrl, Dataset, Dataset]:
    """
    Return a tuple of the following
    - A `RepoUrl` object that represents the URL of the value of
      the `two_files_ds_annex_func_scoped` fixture as a remote repository
    - A `Dataset` object that represents the remote repository,
      i.e., the value of the `two_files_ds_annex_func_scoped` fixture
    - A `Dataset` object that represents a clone of the remote repository
      at the local cache
    """
    repo_url, ds_clone = _establish_repo_url_with_up_to_date_clone(
        two_files_ds_annex_func_scoped, base_cache_path, flask_app
    )
    return repo_url, two_files_ds_annex_func_scoped, ds_clone


@pytest.fixture
def dandi_repo_url_with_up_to_date_clone(dandi_ds, base_cache_path, flask_app):
    """
    Return a tuple of the following
    - A `RepoUrl` object that represents the URL of the value of
      the `dandi_ds` fixture as a remote repository
    - A `Dataset` object that represents the remote repository,
      i.e., the value of the `dandi_ds` fixture
    - A `Dataset` object that represents a clone of the remote repository
      at the local cache
    """
    repo_url, ds_clone = _establish_repo_url_with_up_to_date_clone(
        dandi_ds, base_cache_path, flask_app
    )
    return repo_url, dandi_ds, ds_clone


def _modify_remote(
    remote_ds: Dataset, setting_new_default_branch: bool, adding_file: bool
):
    """
    Modify the remote repository of a local dataset clone

    :param remote_ds: The remote repository is to be modified
    :param setting_new_default_branch: A boolean indicating whether to set a new default
                                       branch for the remote repository
    :param adding_file: A boolean indicating whether to add a new file to the remote
                        repository
    """
    if setting_new_default_branch:
        remote_ds.repo.call_git(["checkout", "-b", "new-branch"])

    if adding_file:
        new_file_name = "new_file.txt"
        with open(remote_ds.pathobj / new_file_name, "w") as f:
            f.write(f"Hello in {new_file_name}\n")
        remote_ds.save(message=f"Add {new_file_name}")


@pytest.fixture
def repo_url_outdated_by_new_file(
    repo_url_with_up_to_date_clone,
) -> tuple[RepoUrl, Dataset, Dataset]:
    """
    This is an extension of the `repo_url_with_up_to_date_clone` fixture with the
    remote repository advanced by a new commit that includes a new file.

    The return of this fixture is the same as the return of
    the `repo_url_with_up_to_date_clone` fixture. However, because of the advancement
    of the remote repository, the `RepoUrl` object and the clone of the remote
    at the local cache are outdated.

    Note: This fixture modifies the remote repository, i.e., the value of the
          `two_files_ds_annex_func_scoped` fixture
    """
    url, remote_ds, local_ds_clone = repo_url_with_up_to_date_clone
    _modify_remote(remote_ds, setting_new_default_branch=False, adding_file=True)
    return url, remote_ds, local_ds_clone


@pytest.fixture
def repo_url_off_sync_by_new_default_branch(
    repo_url_with_up_to_date_clone,
) -> tuple[RepoUrl, Dataset, Dataset]:
    """
    This is an extension of the `repo_url_with_up_to_date_clone` fixture with the
    remote repository's default branch changed to a new branch.

    The return of this fixture is the same as the return of
    the `repo_url_with_up_to_date_clone` fixture. However, because of the change
    of the default branch of the remote repository, the clone of the remote
    at the local cache are out of sync with the remote

    Note: This fixture modifies the remote repository, i.e., the value of the
          `two_files_ds_annex_func_scoped` fixture
    Note: The `RepoUrl` object is not considered outdated because the HEAD of the
          remote is still pointing to the same commit
    """
    url, remote_ds, local_ds_clone = repo_url_with_up_to_date_clone
    _modify_remote(remote_ds, setting_new_default_branch=True, adding_file=False)
    return url, remote_ds, local_ds_clone


@pytest.fixture
def repo_url_outdated_by_new_file_at_new_default_branch(
    repo_url_with_up_to_date_clone,
) -> tuple[RepoUrl, Dataset, Dataset]:
    """
    This is an extension of the `repo_url_with_up_to_date_clone` fixture with the
    remote repository advanced by a new commit at a new default branch
    that includes a new file

    The return of this fixture is the same as the return of
    the `repo_url_with_up_to_date_clone` fixture. However, because of the advancement
    of the remote repository, the `RepoUrl` object and the clone of the remote
    at the local cache are outdated.

    Note: This fixture modifies the remote repository, i.e., the value of the
          `two_files_ds_annex_func_scoped` fixture
    """
    url, remote_ds, local_ds_clone = repo_url_with_up_to_date_clone
    _modify_remote(remote_ds, setting_new_default_branch=True, adding_file=True)
    return url, remote_ds, local_ds_clone
