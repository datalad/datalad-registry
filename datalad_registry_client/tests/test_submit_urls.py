import os
import time

import datalad.api as dl
from datalad.support.exceptions import IncompleteResultsError
from datalad.tests.utils_pytest import assert_in_results
import pytest
import requests

from datalad_registry.utils.url_encoder import url_encode
from datalad_registry_client import DEFAULT_BASE_ENDPOINT
from datalad_registry_client.consts import DEFAULT_ENDPOINT


@pytest.mark.devserver
@pytest.mark.slow
def test_submit_urls_via_local(tmp_path):
    path = str(tmp_path)
    url_encoded = url_encode(path)
    query_url = f"{DEFAULT_ENDPOINT}/urls/{url_encoded}"

    assert requests.get(query_url).json()["status"] == "unknown"

    assert_in_results(
        dl.registry_submit_urls(urls=[path]),
        action="registry-submit-urls",
        url=path,
        status="ok",
    )

    assert requests.get(query_url).json()["status"] != "unknown"

    # Redoing announces.
    res = dl.registry_submit_urls(urls=[path])
    assert_in_results(res, action="registry-submit-urls", url=path, status="ok")


@pytest.mark.devserver
@pytest.mark.slow
def test_submit_multiple_urls():
    pid = os.getpid()
    ts = time.time()
    urls = [
        f"https://www.example.nil/{pid}/{ts}/repo.git",
        f"http://example.test/{pid}/{ts}/dataset.git",
    ]
    query_urls = [f"{DEFAULT_ENDPOINT}/urls/{url_encode(u)}" for u in urls]

    for qu in query_urls:
        assert requests.get(qu).json()["status"] == "unknown"

    res = dl.registry_submit_urls(urls=urls)
    for u in urls:
        assert_in_results(res, action="registry-submit-urls", url=u, status="ok")

    for qu in query_urls:
        assert requests.get(qu).json()["status"] != "unknown"


@pytest.mark.devserver
@pytest.mark.slow
def test_submit_urls_explicit_endpoint(tmp_path):
    path = str(tmp_path)
    # Invalid.
    assert_in_results(
        dl.registry_submit_urls(urls=[path], endpoint="abc", on_failure="ignore"),
        action="registry-submit-urls",
        url=path,
        status="error",
    )

    # Valid, explicit.
    url_encoded = url_encode(path)
    query_url = f"{DEFAULT_ENDPOINT}/urls/{url_encoded}"

    assert_in_results(
        dl.registry_submit_urls(urls=[path], endpoint=DEFAULT_ENDPOINT),
        action="registry-submit-urls",
        url=path,
        status="ok",
    )

    assert requests.get(query_url).json()["status"] != "unknown"


class MockResponse:
    """
    Custom class used to mock the response object returned by
    requests' Session.post() method
    """

    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text


class TestRegistrySubmitURLs:
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
        def mock_post(s, url, json=None):  # noqa: U100 Unused argument
            if url == endpoint:
                return MockResponse(201, "Created")
            else:
                return MockResponse(404, "Not Found")

        monkeypatch.setattr(requests.Session, "post", mock_post)

        if base_endpoint is not None:
            res = dl.registry_submit_urls(
                urls=["http://example.test"], base_endpoint=base_endpoint
            )
        else:
            res = dl.registry_submit_urls(urls=["http://example.test"])

        assert len(res) == 1
        assert res[0]["status"] == "ok"

    def test_handle_successful_response(self, monkeypatch):
        """
        Test handling of a successful response from the server
        """

        # noinspection PyUnusedLocal
        def mock_post(s, url, json=None):  # noqa: U100 Unused argument
            return MockResponse(201, "Created")

        monkeypatch.setattr(requests.Session, "post", mock_post)

        res = dl.registry_submit_urls(urls=["http://example.test"])
        assert len(res) == 1
        assert res[0]["status"] == "ok"

    @pytest.mark.parametrize(
        "status_code, msg_content",
        [
            (400, "Server HTTP response code"),
            (404, "Incorrect endpoint"),
            (409, "already registered"),
            (422, "Unprocessable argument"),
            (500, "Server Error"),
        ],
    )
    def test_handle_error_response(self, status_code, msg_content, monkeypatch):
        """
        Test handling of an error response from the server

        :param status_code: HTTP status code of the response from the server
        :param msg_content: Content contained in the message generated by the client
        """

        # noinspection PyUnusedLocal
        def mock_post(s, url, json=None):  # noqa: U100 Unused argument
            return MockResponse(status_code, "")

        monkeypatch.setattr(requests.Session, "post", mock_post)

        with pytest.raises(IncompleteResultsError, match=msg_content) as exc_info:
            dl.registry_submit_urls(urls=["http://example.test"])

        assert len(exc_info.value.failed) == 1
        assert exc_info.value.failed[0]["status"] == "error"

    def test_multi_urls(self, monkeypatch):
        """
        Test a submission of multiple URLs
        """

        urls = [
            "http://example.test",
            "https://www.datalad.org",
            "https://centerforopenneuroscience.org/",
        ]

        urls_in_set = set(urls)

        # noinspection PyUnusedLocal
        def mock_post(s, url, json=None):  # noqa: U100 Unused argument

            submitted_url = json["url"]

            if submitted_url in urls_in_set:
                urls_in_set.remove(submitted_url)
                return MockResponse(201, "Created")
            else:
                return MockResponse(
                    400, f"Bad Request: submitted unexpected URL: {submitted_url}"
                )

        monkeypatch.setattr(requests.Session, "post", mock_post)

        res = dl.registry_submit_urls(urls=urls)

        assert len(res) == len(urls)
        assert all(r["status"] == "ok" for r in res)
        assert len(urls_in_set) == 0
