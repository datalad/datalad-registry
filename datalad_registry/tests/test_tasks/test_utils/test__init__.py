from pathlib import Path
from string import hexdigits
from uuid import UUID

from datalad.support.exceptions import CommandError
from flask import current_app
import pytest

from datalad_registry.tasks.utils import allocate_ds_path, update_ds_clone

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
    def test_no_update(self, repo_url_with_up_to_date_clone, flask_app):
        """
        Test the case that there is no update in the origin remote of the dataset
        """
        url, origin_remote_ds, initial_ds_clone = repo_url_with_up_to_date_clone

        with flask_app.app_context():
            up_to_date_clone, is_up_to_date_clone_new = update_ds_clone(url)

        assert not is_up_to_date_clone_new
        assert up_to_date_clone.path == initial_ds_clone.path
        assert up_to_date_clone.repo.get_hexsha() == origin_remote_ds.repo.get_hexsha()

    @pytest.mark.parametrize("does_git_merge_fail", [True, False])
    def test_there_is_update(
        self, repo_url_outdated_by_new_file, does_git_merge_fail, monkeypatch, flask_app
    ):
        """
        Test the case that there is an update in the origin remote of the dataset
        """
        url, origin_remote_ds, initial_ds_clone = repo_url_outdated_by_new_file

        with flask_app.app_context():
            if not does_git_merge_fail:

                up_to_date_clone, is_up_to_date_clone_new = update_ds_clone(url)

                assert not is_up_to_date_clone_new
                assert up_to_date_clone.path == initial_ds_clone.path
            else:

                def mock_call_git(*args, **kwargs):
                    if args[1][0] == "merge":
                        raise CommandError("Mock git merge failure")
                    else:
                        return original_call_git(*args, **kwargs)

                from datalad.dataset.gitrepo import GitRepo

                original_call_git = GitRepo.call_git

                monkeypatch.setattr(GitRepo, "call_git", mock_call_git)

                up_to_date_clone, is_up_to_date_clone_new = update_ds_clone(url)

                assert is_up_to_date_clone_new
                assert up_to_date_clone.path != initial_ds_clone.path

        assert up_to_date_clone.repo.get_hexsha() == origin_remote_ds.repo.get_hexsha()

    @pytest.mark.parametrize("does_cloning_fail", [True, False])
    def test_new_default_branch_at_origin_remote(
        self,
        repo_url_off_sync_by_new_default_branch,
        does_cloning_fail,
        monkeypatch,
        flask_app,
    ):
        """
        Test the case that there is a new default branch at the origin remote of the
        dataset
        """
        (
            url,
            origin_remote_ds,
            initial_ds_clone,
        ) = repo_url_off_sync_by_new_default_branch

        with flask_app.app_context():
            if not does_cloning_fail:
                up_to_date_clone, is_up_to_date_clone_new = update_ds_clone(url)

                assert is_up_to_date_clone_new
                assert up_to_date_clone.path != initial_ds_clone.path
                assert (
                    up_to_date_clone.repo.get_hexsha()
                    == origin_remote_ds.repo.get_hexsha()
                )

            else:

                def mock_clone(*_args, **_kwargs):
                    raise RuntimeError("Failure from the mock clone")

                from datalad_registry.tasks import utils as tasks_utils

                monkeypatch.setattr(tasks_utils, "clone", mock_clone)

                with pytest.raises(RuntimeError, match="Failure from the mock clone"):
                    update_ds_clone(url)
