from datetime import datetime

import datalad.api as dl
import pytest
import requests
from yarl import URL

from datalad_registry.blueprints.api.dataset_urls.models import (
    DatasetURLRespModel,
    DatasetURLs,
)
from datalad_registry_client import DEFAULT_BASE_ENDPOINT


class MockResponse:
    """
    Custom class used to mock the response object returned by
    requests' Session.get() method
    """

    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text


dataset_url_resp_model_template = dict(
    id=2,
    ds_id="2a0b7b7b-a984-4c4a-844c-be3132291d7b",
    describe="1234",
    annex_key_count=30,
    annexed_files_in_wt_count=45,
    annexed_files_in_wt_size=100,
    last_update=datetime(2008, 7, 18, 18, 34, 32),
    git_objects_kb=1200,
    processed=True,
)


def test_register():
    """
    Test that `registry_get_urls` is registered with DataLad
    """
    import datalad.api as ds

    assert hasattr(ds, "registry_get_urls")


class TestRegistryGetURLs:
    @pytest.mark.parametrize(
        "base_endpoint, endpoint",
        [
            (None, DEFAULT_BASE_ENDPOINT + "/dataset-urls"),
            (
                "http://127.0.0.1:5000/api/v2",
                "http://127.0.0.1:5000/api/v2/dataset-urls",
            ),
            (
                "http://127.0.0.1:5000/api/v2/",
                "http://127.0.0.1:5000/api/v2/dataset-urls",
            ),
            ("http://127.0.0.1:5000/api///", "http://127.0.0.1:5000/api/dataset-urls"),
        ],
    )
    def test_endpoint_construction(self, base_endpoint, endpoint, monkeypatch):
        """
        Verify the correctness of the endpoint construction.
        """

        # noinspection PyUnusedLocal
        def mock_get(s, url):  # noqa: U100 Unused argument
            requested_endpoint = str(URL(url).with_query({}))
            if requested_endpoint == endpoint:
                # noinspection PyTypeChecker
                return MockResponse(
                    200,
                    DatasetURLs(
                        __root__=[
                            DatasetURLRespModel(
                                **dataset_url_resp_model_template,
                                url="https://www.example.com"
                            )
                        ]
                    ).json(),
                )
            else:
                return MockResponse(404, "Not Found")

        monkeypatch.setattr(requests.Session, "get", mock_get)

        if base_endpoint is not None:
            res = dl.registry_get_urls(cache_path="a/b/c", base_endpoint=base_endpoint)
        else:
            res = dl.registry_get_urls()

        assert len(res) == 1
        assert res[0]["status"] == "ok"
