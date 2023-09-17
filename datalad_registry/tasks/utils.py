# This file is for defining any tools, utilities, or helpers that are in support
# of the Celery tasks
from pathlib import Path
from uuid import uuid4

from flask import current_app

from datalad_registry.models import RepoUrl


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
    pass
