from pathlib import Path
from string import hexdigits
from uuid import UUID

from flask import current_app

from datalad_registry.models import RepoUrl, db
from datalad_registry.tasks.utils import allocate_ds_path, update_ds_clone
from datalad_registry.utils.datalad_tls import clone

_PATH_NAME_CHARS = hexdigits[:-6]


class TestAllocateDsPath:
    def test_format(self, flask_app):
        with flask_app.app_context():
            path = allocate_ds_path()

            path_parts = path.parts

            assert len(path_parts) == 3

            assert len(path_parts[0]) == 3
            assert len(path_parts[1]) == 3
            assert len(path_parts[2]) == 26

            assert all(c in _PATH_NAME_CHARS for c in "".join(path_parts))

    def test_uniqueness(self, flask_app):
        with flask_app.app_context():
            path1 = allocate_ds_path()
            path2 = allocate_ds_path()

            assert path1 != path2

    def test_collision_with_existing_directory(self, flask_app, monkeypatch):
        """
        Test that `allocate_ds_path` can never "knowingly" allocate a path that is
        already in existence as a directory
        """
        ref_uuid = UUID("76a62ed3-7da9-41a4-bc41-dd5b72f14bc7")
        ref_path = Path(ref_uuid.hex[:3], ref_uuid.hex[3:6], ref_uuid.hex[6:])

        final_uuid = UUID("232310ab-18e4-4427-8857-95bdb32a2afd")
        final_path = Path(final_uuid.hex[:3], final_uuid.hex[3:6], final_uuid.hex[6:])

        def mock_uuid4_generator():
            for _ in range(3):
                yield ref_uuid
            yield final_uuid

        def mock_uuid4():
            return next(mock_uuid4_iterator)

        mock_uuid4_iterator = mock_uuid4_generator()

        with flask_app.app_context():
            # Create a directory with the same name as the one that would be generated
            (current_app.config["DATALAD_REGISTRY_DATASET_CACHE"] / ref_path).mkdir(
                parents=True, exist_ok=False
            )

            from datalad_registry.tasks import utils as tasks_utils

            monkeypatch.setattr(tasks_utils, "uuid4", mock_uuid4)

            assert allocate_ds_path() == final_path


class TestUpdateDsClone:
    def test_no_update(self, two_files_ds_annex, flask_app):
        """
        Test the case that there is no update in the origin remote of the dataset
        """
        base_cache_path = flask_app.config["DATALAD_REGISTRY_DATASET_CACHE"]

        clone_path_relative = "a/b/c"

        ds_clone = clone(
            source=two_files_ds_annex,
            path=base_cache_path / clone_path_relative,
            on_failure="stop",
            result_renderer="disabled",
        )

        # Add representation of the URL to the database
        url = RepoUrl(
            url=two_files_ds_annex.path, processed=True, cache_path=clone_path_relative
        )
        # noinspection DuplicatedCode
        with flask_app.app_context():
            db.session.add(url)
            db.session.commit()

            up_to_date_clone, is_up_to_date_clone_new = update_ds_clone(url)

        assert not is_up_to_date_clone_new
        assert up_to_date_clone.path == ds_clone.path
        assert up_to_date_clone.repo.get_hexsha() == ds_clone.repo.get_hexsha()

    def test_there_is_update(self, two_files_ds_annex_func_scoped, flask_app):
        """
        Test the case that there is an update in the origin remote of the dataset
        """
        base_cache_path = flask_app.config["DATALAD_REGISTRY_DATASET_CACHE"]

        clone_path_relative = "a/b/c"

        ds_clone = clone(
            source=two_files_ds_annex_func_scoped,
            path=base_cache_path / clone_path_relative,
            on_failure="stop",
            result_renderer="disabled",
        )

        original_head_hexsha = two_files_ds_annex_func_scoped.repo.get_hexsha()

        # Modify the dataset in the origin remote, `two_files_ds_annex_func_scoped`
        # by adding a new file
        new_file_name = "new_file.txt"
        with open(two_files_ds_annex_func_scoped.pathobj / new_file_name, "w") as f:
            f.write(f"Hello in {new_file_name}\n")
        two_files_ds_annex_func_scoped.save(message=f"Add {new_file_name}")

        new_head_hexsha = two_files_ds_annex_func_scoped.repo.get_hexsha()

        assert new_head_hexsha != original_head_hexsha

        # Add representation of the URL to the database
        url = RepoUrl(
            url=two_files_ds_annex_func_scoped.path,
            processed=True,
            cache_path=clone_path_relative,
        )
        # noinspection DuplicatedCode
        with flask_app.app_context():
            db.session.add(url)
            db.session.commit()

            up_to_date_clone, is_up_to_date_clone_new = update_ds_clone(url)

        assert not is_up_to_date_clone_new
        assert up_to_date_clone.path == ds_clone.path
        assert up_to_date_clone.repo.get_hexsha() == ds_clone.repo.get_hexsha()
