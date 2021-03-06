import subprocess as sp

import datalad.api as dl
import pytest
import requests
from datalad.tests.utils import assert_in_results

from datalad_registry.utils import url_encode

ENDPOINT = "http://127.0.0.1:5000/v1"


@pytest.mark.slow
def test_submit_not_dataset(tmp_path):
    sp.run(["git", "init"], cwd=str(tmp_path))
    ds = dl.Dataset(tmp_path)
    with pytest.raises(ValueError):
        ds.registry_submit()


@pytest.mark.devserver
@pytest.mark.slow
def test_submit_via_local(tmp_path):

    ds = dl.Dataset(tmp_path / "ds").create()
    ds_id = ds.id

    url_encoded = url_encode(ds.path)
    query_url = f"{ENDPOINT}/datasets/{ds_id}/urls/{url_encoded}"

    assert requests.get(query_url).json()["status"] == "unknown"

    # If sibling is not specified, URL is required.
    with pytest.raises(ValueError):
        ds.registry_submit()

    assert_in_results(
        ds.registry_submit(url=ds.path),
        action="registry-submit", type="dataset",
        path=ds.path, status="ok")

    assert requests.get(query_url).json()["status"] != "unknown"

    # Redoing announces.
    res = ds.registry_submit(url=ds.path)
    assert_in_results(
        res,
        action="registry-submit", type="dataset",
        path=ds.path, status="ok")


@pytest.mark.slow
def test_submit_invalid_siblings(tmp_path):
    ds = dl.Dataset(tmp_path).create()

    # Unknown sibling fails.
    with pytest.raises(ValueError):
        ds.registry_submit(sibling="foo")

    # So does a sibling without a URL.
    ds.config.set("remote.no_url.fetch", "blah", where="local")
    with pytest.raises(ValueError):
        ds.registry_submit(sibling="no_url")


@pytest.mark.devserver
@pytest.mark.slow
def test_submit_via_sibling(tmp_path):
    ds_sib = dl.Dataset(tmp_path / "sib").create()
    ds = dl.clone(ds_sib.path, str(tmp_path / "clone"))
    ds_id = ds.id

    url_encoded = url_encode(ds_sib.path)
    query_url = f"{ENDPOINT}/datasets/{ds_id}/urls/{url_encoded}"

    assert requests.get(query_url).json()["status"] == "unknown"

    assert_in_results(
        ds.registry_submit(sibling="origin"),
        action="registry-submit", type="dataset",
        path=ds.path, status="ok")

    assert requests.get(query_url).json()["status"] != "unknown"


@pytest.mark.devserver
@pytest.mark.slow
def test_submit_explicit_endpoint(tmp_path):
    ds = dl.Dataset(tmp_path / "ds").create()
    ds_id = ds.id

    # Invalid.
    assert_in_results(
        ds.registry_submit(url=ds.path, endpoint="abc", on_failure="ignore"),
        action="registry-submit", type="dataset",
        path=ds.path, status="error")

    # Valid, explicit.
    url_encoded = url_encode(ds.path)
    query_url = f"{ENDPOINT}/datasets/{ds_id}/urls/{url_encoded}"

    assert_in_results(
        ds.registry_submit(url=ds.path, endpoint=ENDPOINT),
        action="registry-submit", type="dataset",
        path=ds.path, status="ok")

    assert requests.get(query_url).json()["status"] != "unknown"
