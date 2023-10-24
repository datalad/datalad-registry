# This file is for defining any tools, utilities, or helpers that are in support
# of the Celery tasks
from pathlib import Path
from uuid import uuid4

from celery.utils.log import get_task_logger
from datalad.api import Dataset
from datalad.distribution.dataset import require_dataset
from datalad.support.exceptions import CommandError
from datalad.utils import rmtree as rm_ds_tree
from flask import current_app

from datalad_registry.models import RepoUrl
from datalad_registry.utils.datalad_tls import (
    clone,
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
    Validate that a given RepoUrl has been marked processed

    :raise: ValueError if the given RepoUrl has not been marked processed

    Note: This function is meant to be called inside a Celery task for it requires
          an active application context of the Flask app
    """

    if not repo_url.processed:
        raise ValueError(
            f"RepoUrl {repo_url.url}, of ID: {repo_url.id}, has not been processed yet"
        )


def update_ds_clone(repo_url: RepoUrl) -> tuple[Dataset, bool]:
    """
    Update the local clone of the dataset at a given URL

    :param repo_url: The RepoUrl object representing the given URL
    :return: A tuple containing the following two elements:
             - An up-to-date clone of the dataset at the given URL that exists in the
               cache
               Note: This can be a newly created clone.
             - A boolean indicating if the dataset clone, the first element of
               the returning tuple, is a newly created clone of the dataset,
               which is different from the one located at the current value of
               `cache_path` of the given RepoUrl object
    :raise ValueError: If the given URL has not been processed

    Note: This function is meant to be called inside a Celery task for it requires
          an active application context of the Flask app
    """

    def reclone_ds() -> Dataset:
        """
        Reclone the dataset at the given URL to a new directory in the cache

        :return: The new dataset clone
        """
        # Allocate a new path for the new clone of the dataset
        ds_path_relative = allocate_ds_path()
        ds_path_absolute = base_cache_path / ds_path_relative

        # Create a directory at the newly allocated path
        ds_path_absolute.mkdir(parents=True, exist_ok=False)

        try:
            # Clone the dataset at the given URL to the newly created directory
            ds_clone = clone(
                source=repo_url.url,
                path=ds_path_absolute,
                on_failure="stop",
                result_renderer="disabled",
            )
        except Exception:
            lgr.debug(
                "Failed to clone the dataset at the given URL, %s, to a new directory",
                repo_url.url,
                exc_info=True,
            )

            # Delete the newly created directory for cloning the dataset
            rm_ds_tree(ds_path_absolute)

            raise
        else:
            return ds_clone

    # Validate that the given RepoUrl has been marked processed
    validate_url_is_processed(repo_url)

    base_cache_path: Path = current_app.config["DATALAD_REGISTRY_DATASET_CACHE"]

    current_ds_clone_path = repo_url.cache_path_abs
    assert current_ds_clone_path is not None

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
            lgr.debug(
                "Failed to merge the origin upstream branch. "
                "A new clone of the dataset at the given URL will be made"
                " in a new directory",
                exc_info=True,
            )

            # Make a new clone of the dataset at the given URL at a new directory
            return reclone_ds(), True
        else:
            # Merge the git-annex branch if the current dataset is an annex repo
            if current_ds_clone.repo.is_with_annex():
                current_ds_clone.repo.call_annex(["merge"])

            return current_ds_clone, False
    else:
        # Make a new clone of the dataset at the given URL at a new directory
        return reclone_ds(), True
