import pytest
import requests
import time

import datalad.api as dl
from datalad.tests.utils import assert_in_results

from datalad_registry.utils import url_encode

ENDPOINT = "http://127.0.0.1:5000/v1"


@pytest.mark.devserver
@pytest.mark.slow
def test_announce_unknown(tmp_path):
    ds = dl.Dataset(tmp_path / "ds").create()
    assert_in_results(
        ds.registry_announce_update(url=ds.path, on_failure="ignore"),
        action="registry-announce-update", type="dataset",
        path=ds.path, status="error")


@pytest.mark.devserver
@pytest.mark.slow
def test_submit_and_announce(tmp_path):
    ds = dl.Dataset(tmp_path / "ds").create()
    ds_id = ds.id

    url_encoded = url_encode(ds.path)
    query_url = f"{ENDPOINT}/datasets/{ds_id}/urls/{url_encoded}"

    assert_in_results(
        ds.registry_submit(url=ds.path),
        action="registry-submit", type="dataset",
        path=ds.path, status="ok")

    t_initial = time.time()
    for i in range(10):
        if requests.get(query_url).json()["status"] == "known":
            break
        time.sleep(0.1)
    else:
        t_final = time.time()
        raise AssertionError(
            "Submitted URL still not known after waiting ~{:03.2f} seconds"
            .format(t_final - t_initial))

    assert_in_results(
        ds.registry_announce_update(url=ds.path),
        action="registry-announce-update", type="dataset",
        path=ds.path, status="ok")
