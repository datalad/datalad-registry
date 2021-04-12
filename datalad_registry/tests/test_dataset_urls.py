import pytest
from unittest.mock import patch

from datalad_registry.utils import url_encode
from datalad_registry.tests.utils import init_repo


def test_urls_get_empty(client, ds_id):
    data = client.get(f"/v1/datasets/{ds_id}/urls").get_json()
    assert data["ds_id"] == ds_id
    assert data["urls"] == []


def test_urls_post_invalid_data(client, ds_id):
    response = client.post(f"/v1/datasets/{ds_id}/urls", json={})
    assert response.status_code == 400


@pytest.mark.parametrize("bad_url", ["a", "abcd"])
def test_url_bad_url_get(client, ds_id, bad_url):
    response = client.get(f"/v1/datasets/{ds_id}/urls/{bad_url}")
    assert response.status_code == 400


def test_url_unnkown_url_announce(client, ds_id):
    url = "doesnt.matter"
    url_encoded = url_encode(url)
    response = client.patch(f"/v1/datasets/{ds_id}/urls/{url_encoded}")
    assert response.status_code == 404


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

    r_post = client.post(f"/v1/datasets/{ds_id}/urls", json={"url": url})
    assert r_post.status_code == 202
    data_post = r_post.get_json()
    assert data_post["url_encoded"] == url_encoded

    urls = client.get(f"/v1/datasets/{ds_id}/urls").get_json()["urls"]
    assert urls == [url]
    assert get_status() == "known"

    # And again.
    r_post2 = client.post(f"/v1/datasets/{ds_id}/urls", json={"url": url})
    assert r_post2.status_code == 202
    assert get_status() == "known"
