from pathlib import Path
from string import hexdigits
from uuid import UUID

from flask import current_app

from datalad_registry.utils import allocate_ds_path

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

            from datalad_registry.utils import misc

            monkeypatch.setattr(misc, "uuid4", mock_uuid4)

            assert allocate_ds_path() == final_path
