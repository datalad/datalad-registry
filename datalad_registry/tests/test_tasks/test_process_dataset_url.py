from datetime import datetime, timezone
from itertools import chain
import os
from pathlib import Path
from typing import Optional, Union

from flask import current_app
import pytest
from sqlalchemy import inspect

from datalad_registry.models import URL, db
from datalad_registry.tasks import process_dataset_url


def is_there_file_in_tree(top: Union[Path, str]) -> bool:
    """
    Check if there is any file in a directory tree rooted at `top`
    """
    for _ in chain.from_iterable((t[2] for t in os.walk(top))):
        return True
    return False


def is_dataset_url_unprocessed(dataset_url_id: int) -> bool:
    """
    Check if the given dataset URL, identified by ID, is unprocessed

    :raise ValueError: If the given dataset URL ID is invalid

    Note: This check also verifies that the other fields of the dataset URL are also
          unmodified since they are initialized.

    Note: This function must be called within a Flask application context so that
          it has the needed access to the database.
    """

    fields = inspect(URL).columns.keys()  # type: ignore[union-attr]
    default_none_fields = [
        f
        for f in fields
        if (f != "id" and f != "url" and f != "update_announced" and f != "processed")
    ]

    dataset_url: Optional[URL] = db.session.execute(
        db.select(URL).filter_by(id=dataset_url_id)
    ).scalar()

    if dataset_url is None:
        raise ValueError(f"Invalid dataset URL ID: {dataset_url_id}")

    return (not dataset_url.processed) and all(
        getattr(dataset_url, f) is None for f in default_none_fields
    )


class TestProcessDatasetUrl:
    @pytest.mark.usefixtures("populate_db_with_unprocessed_dataset_urls")
    @pytest.mark.parametrize("invalid_dataset_url_id", [-100, -1, 0, 1, 7, 8, 99])
    def test_invalid_dataset_url_id(self, invalid_dataset_url_id, flask_app):
        """
        Test the case that the given dataset URL id is not valid, i.e. no dataset URL
        having the given id exists in the database
        """
        with flask_app.app_context():
            with pytest.raises(ValueError):
                process_dataset_url(invalid_dataset_url_id)

    @pytest.mark.usefixtures("populate_db_with_unprocessed_dataset_urls")
    @pytest.mark.parametrize("dataset_url_id", [2, 3, 4, 5, 6])
    def test_valid_dataset_url(self, dataset_url_id, flask_app):
        """
        Test the case that the given dataset URL by id is valid, i.e. the URL is indeed
        the URL of a datalad dataset
        """
        with flask_app.app_context():
            time_before_processing = datetime.now(timezone.utc)

            process_dataset_url(dataset_url_id)

            time_after_processing = datetime.now(timezone.utc)

            # Retrieve the dataset URL after processing
            dataset_url: Optional[URL] = db.session.execute(
                db.select(URL).filter_by(id=dataset_url_id)
            ).scalar()

            assert (
                time_before_processing
                <= dataset_url.last_update_dt
                <= time_after_processing
            )
            assert dataset_url.processed
            assert dataset_url.cache_path is not None

    @pytest.mark.usefixtures("populate_db_with_unprocessed_dataset_urls")
    @pytest.mark.parametrize("dataset_url_id", [3, 4, 5])
    def test_clone_failure(self, dataset_url_id, flask_app, monkeypatch):
        """
        Test the case that the cloning of the dataset fails when processing the dataset
        URL
        """

        # noinspection PyUnusedLocal
        def mock_clone(*args, **kwargs):  # noqa: U100
            raise RuntimeError("Mocked clone failure")

        from datalad_registry import tasks as datalad_registry_tasks

        monkeypatch.setattr(datalad_registry_tasks, "clone", mock_clone)

        with flask_app.app_context():
            with pytest.raises(RuntimeError):
                process_dataset_url(dataset_url_id)

            # Check that the dataset URL not been modified in the database
            assert is_dataset_url_unprocessed(dataset_url_id)

            # Ensure that there shouldn't be any file in the base cache directory
            # as result of the failed processing
            assert not is_there_file_in_tree(
                Path(current_app.config["DATALAD_REGISTRY_DATASET_CACHE"])
            )

    @pytest.mark.usefixtures("populate_db_with_unprocessed_dataset_urls")
    @pytest.mark.parametrize("dataset_url_id", [2, 3, 4, 5, 6])
    def test_update_info_failure(self, dataset_url_id, flask_app, monkeypatch):
        """
        Test the case that `_update_dataset_url_info()` fails
        """

        from datalad_registry import tasks

        # noinspection PyUnusedLocal
        def mock_update_dataset_url_info(
            *args, **kwargs  # noqa: U100 (Unused argument)
        ):
            raise RuntimeError("Mock exception")

        monkeypatch.setattr(
            tasks, "_update_dataset_url_info", mock_update_dataset_url_info
        )

        with flask_app.app_context():
            with pytest.raises(RuntimeError):
                process_dataset_url(dataset_url_id)

            # Check that the dataset URL not been modified in the database
            assert is_dataset_url_unprocessed(dataset_url_id)

            # Ensure that there shouldn't be any file in the base cache directory
            # as result of the failed processing
            assert not is_there_file_in_tree(
                Path(current_app.config["DATALAD_REGISTRY_DATASET_CACHE"])
            )

    @pytest.mark.usefixtures("populate_db_with_unprocessed_dataset_urls")
    def test_repeated_processing(self, flask_app):
        """
        Test the case that a dataset URL is processed multiple times
        """

        url_id = 5  # URL ID of the `two_files_ds_annex` dataset

        with flask_app.app_context():
            base_cache_path = Path(current_app.config["DATALAD_REGISTRY_DATASET_CACHE"])

            dataset_url: Optional[URL] = db.session.execute(
                db.select(URL).filter_by(id=url_id)
            ).scalar()

            ds_cache_paths: list[Path] = []
            for _ in range(3):
                process_dataset_url(url_id)
                ds_cache_paths.append(base_cache_path / Path(dataset_url.cache_path))

            # Verify that only the cache directory created
            # by the last processing remains
            assert not ds_cache_paths[0].is_dir()
            assert not ds_cache_paths[1].is_dir()
            assert ds_cache_paths[2].is_dir()

            assert dataset_url.processed
