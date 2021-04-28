import pytest

from datalad_registry.tests.utils import init_repo
from datalad_registry.utils import url_encode


def test_urls_get_empty(client, ds_id):
    data = client.get(f"/v1/datasets/{ds_id}/urls").get_json()
    assert data["ds_id"] == ds_id
    assert data["urls"] == []


@pytest.mark.parametrize("bad_url", ["a", "abcd"])
def test_url_bad_url_get(client, ds_id, bad_url):
    response = client.get(f"/v1/datasets/{ds_id}/urls/{bad_url}")
    assert response.status_code == 400


def test_register_url(client, ds_id, tmp_path):
    dset = tmp_path / "ds"
    dset.mkdir()

    url = "file:///" + str(dset)
    url_encoded = url_encode(url)

    def get_status():
        response = client.get(
            f"/v1/datasets/{ds_id}/urls/{url_encoded}")
        return response.get_json()["status"]

    assert get_status() == "unknown"

    init_repo(str(dset))

    r_patch = client.patch(f"/v1/datasets/{ds_id}/urls/{url_encoded}")
    assert r_patch.status_code == 202

    urls = client.get(f"/v1/datasets/{ds_id}/urls").get_json()["urls"]
    assert urls == [url]
    assert get_status() == "known"

    # And again.
    r_patch2 = client.patch(f"/v1/datasets/{ds_id}/urls/{url_encoded}")
    assert r_patch2.status_code == 202
    assert get_status() == "known"
