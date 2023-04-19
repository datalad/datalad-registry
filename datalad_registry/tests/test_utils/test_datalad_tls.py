import pytest

from datalad_registry.utils.datalad_tls import clone

_TEST_DATASET_URL = "https://github.com/datalad/testrepo--minimalds.git"
_TEST_DATASET_ID = "e7f3d914-e971-11e8-a371-f0d5bf7b5561"


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
            clone(source=_TEST_DATASET_URL, path=tmp_path, return_type=return_type)

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
            clone(source=_TEST_DATASET_URL, path=tmp_path)

    def test_clone_minimal_dataset(self, tmp_path):
        """
        Test cloning a minimal dataset used for testing
        """
        ds = clone(source=_TEST_DATASET_URL, path=tmp_path)
        assert ds.id == _TEST_DATASET_ID
