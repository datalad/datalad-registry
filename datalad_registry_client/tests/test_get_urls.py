from datetime import datetime

import datalad.api as dl
from datalad.support.exceptions import IncompleteResultsError
from multidict import MultiDict
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
    metadata=[],
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

    @pytest.mark.parametrize(
        "cache_path",
        [
            "a/b/c",
            "/a/b/c/",
            "/a/b/c///",
            "8f7/834/cd26484ce78ece48ef811268e2",
            "/8f7/834/cd26484ce78ece48ef811268e2/",
            "/cache/98e/f22/a2d0d240f8a11936e8686ce1ed",
        ],
    )
    def test_query_construction(self, cache_path, monkeypatch):
        """
        Verify the correctness of the query construction
        in requests to the server
        """

        # noinspection PyUnusedLocal
        def mock_get(s, url):  # noqa: U100 Unused argument
            if URL(url).query == MultiDict(cache_path=cache_path):
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

        res = dl.registry_get_urls(cache_path=cache_path)

        assert len(res) == 1
        assert res[0]["status"] == "ok"

    @pytest.mark.parametrize(
        "response_urls",
        [
            ["https://www.example.com"],
            [
                "https://www.example.com",
                "https://centerforopenneuroscience.org/",
                "https://www.datalad.org/",
            ],
        ],
    )
    def test_handle_successful_response(self, response_urls: list[str], monkeypatch):
        """
        Test handling of a successful response from the server
        """

        # noinspection PyUnusedLocal
        def mock_get(s, url):  # noqa: U100 Unused argument
            # noinspection PyTypeChecker
            return MockResponse(
                200,
                DatasetURLs(
                    __root__=[
                        DatasetURLRespModel(
                            **dataset_url_resp_model_template, url=response_url
                        )
                        for response_url in response_urls
                    ]
                ).json(),
            )

        monkeypatch.setattr(requests.Session, "get", mock_get)

        res = dl.registry_get_urls(cache_path="a/b/c")

        assert len(res) == 1
        assert res[0]["status"] == "ok"
        assert str(response_urls) in res[0]["message"]
        assert "error_message" not in res[0]

    @pytest.mark.parametrize(
        "status_code, msg_content",
        [
            (400, "Server HTTP response code"),
            (404, "Incorrect target URL"),
            (422, "Unprocessable argument"),
            (500, "Server error"),
        ],
    )
    def test_handle_error_response(self, status_code, msg_content, monkeypatch):
        """
        Test handling of an error response from the server

        :param status_code: HTTP status code of the response from the server
        :param msg_content: Content contained in the message generated by the client
        """

        # noinspection PyUnusedLocal
        def mock_get(s, url):  # noqa: U100 Unused argument
            return MockResponse(status_code, "")

        monkeypatch.setattr(requests.Session, "get", mock_get)

        with pytest.raises(IncompleteResultsError, match=msg_content) as exc_info:
            dl.registry_get_urls(cache_path="/a/b/c")

        assert len(exc_info.value.failed) == 1
        assert exc_info.value.failed[0]["status"] == "error"
        assert msg_content in exc_info.value.failed[0]["error_message"]
        assert "message" not in exc_info.value.failed[0]
