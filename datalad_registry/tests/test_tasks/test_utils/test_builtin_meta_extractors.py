from datalad_registry.tasks.utils.builtin_meta_extractors import (
    dlreg_dandiset_meta_extract,
)
from datalad_registry.utils.datalad_tls import get_head_describe


def test_dlreg_dandiset_meta_extract(dandi_repo_url_with_up_to_date_clone, flask_app):

    repo_url = dandi_repo_url_with_up_to_date_clone[0]
    ds_clone = dandi_repo_url_with_up_to_date_clone[2]

    with flask_app.app_context():
        url_metadata = dlreg_dandiset_meta_extract(repo_url)

    assert url_metadata.dataset_describe == get_head_describe(ds_clone)
    assert url_metadata.dataset_version == ds_clone.repo.get_hexsha()
    assert url_metadata.extractor_name == "dandi:dandiset"
    assert url_metadata.extractor_version == "0.0.1"
    assert url_metadata.extraction_parameter == {}
    assert url_metadata.extracted_metadata == {"name": "test-dandi-ds"}
    assert url_metadata.url == repo_url
