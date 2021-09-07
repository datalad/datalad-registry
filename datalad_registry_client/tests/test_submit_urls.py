import os
import time
import subprocess as sp

import datalad.api as dl
import pytest
import requests
from datalad.tests.utils import assert_in_results

from datalad_registry.utils import url_encode
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
