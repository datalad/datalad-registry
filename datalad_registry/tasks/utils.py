# This file is for defining any tools, utilities, or helpers that are in support
# of the Celery tasks
from pathlib import Path
from uuid import uuid4

from celery.utils.log import get_task_logger
from datalad.distribution.dataset import require_dataset
from datalad.support.exceptions import CommandError
from flask import current_app

from datalad_registry.models import RepoUrl
from datalad_registry.utils.datalad_tls import (
    get_origin_default_branch,
    get_origin_upstream_branch,
)

lgr = get_task_logger(__name__)


def allocate_ds_path() -> Path:
    """
    Allocate a path for cloning a dataset into the cache

    :return: The allocated path for cloning a dataset into the cache. This path is
             a relative path to the cache directory and guaranteed to
             not yet and not going to be allocated for storing another dataset.

    Note: This allocated path is based on a randomly generated UUID
    Note: The execution of this function requires an active application context of Flask
    Note: This function always returns a path that, when expressed in `str` form, is
          34 characters long. 32 characters for the UUID as hex string plus two path
          component separators, e.g. `/` in *nix
    """

    # The while loop with the checking of the existence of the generated path can be
    # deemed as excessive by some. However, having it further ensures the returned path
    # is really one that is uniquely allocated for the cloning of a particular dataset
    # and not any other dataset.
    while True:
        uuid = uuid4().hex
        path = Path(uuid[:3], uuid[3:6], uuid[6:])

        if not (current_app.config["DATALAD_REGISTRY_DATASET_CACHE"] / path).is_dir():
            return path


def validate_url_is_processed(repo_url: RepoUrl) -> None:
    """
    Validate that a given RepoUrl has been marked processed and has a cache path

    :raise: ValueError if the given RepoUrl has not been marked processed
    :raise: Otherwise, AssertionError if the given RepoUrl has no cache path

    Note: This function is meant to be called inside a Celery task for it requires
          an active application context of the Flask app
    """

    if not repo_url.processed:
        raise ValueError(
            f"RepoUrl {repo_url.url}, of ID: {repo_url.id}, has not been processed yet"
        )

    assert (
        repo_url.cache_path is not None
    ), "Encountered a processed RepoUrl with no cache path"


def update_ds_clone(repo_url: RepoUrl) -> tuple[Path, bool]:
    """
    Update the local clone of the dataset at a given URL

    :param repo_url: The RepoUrl object representing the given URL
    :return: A tuple containing the following two elements:
             - The path to an up-to-date clone of the dataset at the given URL
               Note: This path is a relative path to the base cache directory
             - A boolean indicating if the path, the first element of the tuple,
               is a newly created directory for a new clone of the dataset, which is
               different from the current value of `cache_path` of the given RepoUrl
               object

    Note: This function is meant to be called inside a Celery task for it requires
          an active application context of the Flask app
    """
    validate_url_is_processed(repo_url)

    base_cache_path: Path = current_app.config["DATALAD_REGISTRY_DATASET_CACHE"]

    current_ds_clone_path = base_cache_path / repo_url.cache_path

    current_ds_clone = require_dataset(
        current_ds_clone_path, check_installed=True, purpose="update"
    )

    current_ds_clone.repo.call_git(["fetch"])

    # The current default branch of the origin remote, the copy of the dataset
    # located at the given URL, that the local clone is tracking
    current_origin_default_branch = get_origin_default_branch(current_ds_clone)

    # The upstream branch at the origin remote of the current local branch
    origin_upstream_branch = get_origin_upstream_branch(current_ds_clone)

    if origin_upstream_branch == current_origin_default_branch:
        try:
            current_ds_clone.repo.call_git(
                ["merge", "--ff-only", f"origin/{origin_upstream_branch}"]
            )
        except CommandError:
            # Log the CommandError

            # Make a new clone of the dataset at the given URL at a new directory

            raise NotImplementedError
        else:
            # Merge the git-annex branch if the current dataset is an annex repo
            if current_ds_clone.repo.is_with_annex():
                current_ds_clone.repo.call_annex(["merge"])

            return current_ds_clone_path, False
    else:
        # Make a new clone of the dataset at the given URL at a new directory
        raise NotImplementedError
