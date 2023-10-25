import importlib

import pytest

from datalad_registry.utils.datalad_tls import get_head_describe


@pytest.fixture
def load_builtin_meta_extractors_without_c_safe_loader(monkeypatch):
    """
    This fixture reloads the builtin meta extractors module without
    the C-based YAML loader, `CSafeLoader`, in the `yaml` package.
    """

    with monkeypatch.context() as m:
        import yaml

        from datalad_registry.tasks.utils import builtin_meta_extractors

        # Remove the C-based YAML loader, `CSafeLoader`, from the `yaml` package
        m.delattr(yaml, "CSafeLoader", raising=False)

        # Reload the builtin meta extractors module
        importlib.reload(builtin_meta_extractors)

        yield

    # Reload the builtin meta extractors module
    # in the original state of the `yaml` package
    importlib.reload(builtin_meta_extractors)


@pytest.mark.usefixtures("load_builtin_meta_extractors_without_c_safe_loader")
def test_fallback_to_safe_loader():
    """
    Test that the builtin meta extractors module falls back to the Python-based YAML
    loader, `SafeLoader`, when the C-based YAML loader, `CSafeLoader`, is not available
    """
    from datalad_registry.tasks.utils import builtin_meta_extractors

    assert builtin_meta_extractors.SafeLoader.__name__ == "SafeLoader"


class TestDlregDandisetMetaExtract:
    def test_valid_input(self, dandi_repo_url_with_up_to_date_clone, flask_app):
        """
        Test the case that the argument `url` is a valid `RepoUrl` object with a
        valid corresponding dandi dataset in the local cache
        """
        from datalad_registry.tasks.utils.builtin_meta_extractors import (
            dlreg_dandiset_meta_extract,
        )

        repo_url = dandi_repo_url_with_up_to_date_clone[0]
        ds_clone = dandi_repo_url_with_up_to_date_clone[2]

        with flask_app.app_context():
            url_metadata = dlreg_dandiset_meta_extract(repo_url)

        assert url_metadata.dataset_describe == get_head_describe(ds_clone)
        assert url_metadata.dataset_version == ds_clone.repo.get_hexsha()
        assert url_metadata.extractor_name == "dandi"
        assert url_metadata.extractor_version == "0.0.1"
        assert url_metadata.extraction_parameter == {}
        assert url_metadata.extracted_metadata == {"name": "test-dandi-ds"}
        assert url_metadata.url == repo_url

    def test_no_document(self, dandi_repo_url_with_up_to_date_clone, flask_app):
        """
        Test the case that the `dandiset.yaml` file has no document
        """
        from datalad_registry.tasks.utils.builtin_meta_extractors import (
            InvalidRequiredFileError,
            dlreg_dandiset_meta_extract,
        )

        repo_url = dandi_repo_url_with_up_to_date_clone[0]
        ds_clone = dandi_repo_url_with_up_to_date_clone[2]

        # Empty the `dandiset.yaml` file
        with open(ds_clone.pathobj / "dandiset.yaml", "w") as f:
            f.write("")

        with flask_app.app_context():
            with pytest.raises(
                InvalidRequiredFileError, match="dandiset.yaml has no document"
            ):
                dlreg_dandiset_meta_extract(repo_url)


class TestDlregMetaExtract:
    def test_unsupported_extractor(
        self, dandi_repo_url_with_up_to_date_clone, flask_app
    ):
        """
        Test the case that the given extractor is not one that is supported
        """
        from datalad_registry.tasks.utils.builtin_meta_extractors import (
            dlreg_meta_extract,
        )

        repo_url = dandi_repo_url_with_up_to_date_clone[0]

        with flask_app.app_context():
            with pytest.raises(
                ValueError, match="unsupported_extractor is not supported"
            ):
                dlreg_meta_extract("unsupported_extractor", repo_url)

    def test_supported_extractor(self, dandi_repo_url_with_up_to_date_clone, flask_app):
        """
        Test the case that the given extractor is one that is supported
        """
        from datalad_registry.tasks.utils.builtin_meta_extractors import (
            dlreg_meta_extract,
        )

        repo_url = dandi_repo_url_with_up_to_date_clone[0]

        with flask_app.app_context():
            url_metadata = dlreg_meta_extract("dandi", repo_url)

        assert url_metadata.extractor_name == "dandi"
