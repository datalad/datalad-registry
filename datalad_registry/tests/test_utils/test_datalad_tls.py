import pytest

from datalad_registry.utils.datalad_tls import clone, get_origin_annex_uuid

_TEST_MIN_DATASET_URL = "https://github.com/datalad/testrepo--minimalds.git"
_TEST_MIN_DATASET_ID = "e7f3d914-e971-11e8-a371-f0d5bf7b5561"


class TestClone:
    @pytest.mark.parametrize(
        "return_type",
        ["generator", "list", "item-or-list"],
    )
    def test_unsupported_kwarg(self, tmp_path, return_type):
        """
        Test the case that the unsupported keyword argument of `return_type`
        is provided
        """
        with pytest.raises(TypeError):
            clone(source=_TEST_MIN_DATASET_URL, path=tmp_path, return_type=return_type)

    @pytest.mark.parametrize(
        "clone_return",
        [None, list(), ["a", "b", "c"]],
    )
    def test_no_dataset_object_produced(self, monkeypatch, tmp_path, clone_return):
        """
        Test the case that no `datalad.api.Dataset` object is produced after
        a successful run of the underlying `datalad.api.clone` function
        """
        from datalad import api as dl

        # noinspection PyUnusedLocal
        def mock_clone(*args, **kwargs):  # noqa: U100 (unused argument)
            return clone_return

        monkeypatch.setattr(dl, "clone", mock_clone)

        with pytest.raises(RuntimeError):
            clone(source=_TEST_MIN_DATASET_URL, path=tmp_path)

    def test_clone_minimal_dataset(self, tmp_path):
        """
        Test cloning a minimal dataset used for testing
        """
        ds = clone(source=_TEST_MIN_DATASET_URL, path=tmp_path)
        assert ds.id == _TEST_MIN_DATASET_ID


class TestGetOriginAnnexUuid:
    def test_origin_annex_uuid_exists(self, tmp_path, empty_ds):
        """
        Test the case that the origin remote has an annex UUID
        """
        ds_clone = clone(source=empty_ds.path, path=tmp_path)
        assert get_origin_annex_uuid(ds_clone) == empty_ds.config.get("annex.uuid")

    def test_origin_annex_uuid_not_exist(self, tmp_path):
        """
        Test the case that the origin remote has no annex UUID
        """
        ds = clone(source=_TEST_MIN_DATASET_URL, path=tmp_path)
        assert get_origin_annex_uuid(ds) is None
