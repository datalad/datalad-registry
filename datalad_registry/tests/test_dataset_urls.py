import pytest
from unittest.mock import patch

from datalad_registry.utils import url_encode
from datalad_registry.tests.utils import init_repo_with_token


def test_token_get(client, dsid):
    url = "doesnt.matter"
    url_encoded = url_encode(url)
    data = client.get(
        f"/v1/datasets/{dsid}/urls/{url_encoded}/token").get_json()
    assert "token" in data
    assert data["dsid"] == dsid
    assert data["ref"] == "refs/datalad-registry/" + data["token"]
    assert data["url"] == url


@pytest.mark.parametrize("bad_url", ["a", "abcd"])
def test_token_bad_url_get(client, dsid, bad_url):
    response = client.get(f"/v1/datasets/{dsid}/urls/{bad_url}/token")
    assert response.status_code == 400


def test_urls_get_empty(client, dsid):
    data = client.get(f"/v1/datasets/{dsid}/urls").get_json()
    assert data["dsid"] == dsid
    assert data["urls"] == []


def test_urls_post_invalid_data(client, dsid):
    response = client.post(f"/v1/datasets/{dsid}/urls", json={})
    assert response.status_code == 400


def test_urls_post_unknown_token(client, dsid):
    response = client.post(f"/v1/datasets/{dsid}/urls",
                           json={"token": "unknown",
                                 "url": "doesnt.matter"})
    assert response.status_code == 400


@pytest.mark.parametrize("bad_url", ["a", "abcd"])
def test_url_bad_url_get(client, dsid, bad_url):
    response = client.get(f"/v1/datasets/{dsid}/urls/{bad_url}")
    assert response.status_code == 400


def test_url_unnkown_url_announce(client, dsid):
    url = "doesnt.matter"
    url_encoded = url_encode(url)
    response = client.patch(f"/v1/datasets/{dsid}/urls/{url_encoded}")
    assert response.status_code == 404


def test_register_url(client, dsid, tmp_path):
    dset = tmp_path / "ds"
    dset.mkdir()

    url = "file:///" + str(dset)
    url_encoded = url_encode(url)

    d_token = client.get(
        f"/v1/datasets/{dsid}/urls/{url_encoded}/token").get_json()

    def get_status():
        response = client.get(
            f"/v1/datasets/{dsid}/urls/{url_encoded}")
        return response.get_json()["status"]

    assert get_status() == "token requested"

    init_repo_with_token(str(dset), d_token)

    r_post = client.post(f"/v1/datasets/{dsid}/urls", json=d_token)
    assert r_post.status_code == 202
    data_post = r_post.get_json()
    assert data_post["url_encoded"] == url_encoded

    urls = client.get(f"/v1/datasets/{dsid}/urls").get_json()["urls"]
    assert urls == [url]
    assert get_status() == "known"

    # And again.
    d_token2 = client.get(
        f"/v1/datasets/{dsid}/urls/{url_encoded}/token").get_json()
    r_post2 = client.post(f"/v1/datasets/{dsid}/urls", json=d_token2)
    assert r_post2.status_code == 202
    assert get_status() == "known"


def test_register_url_expired_token(client, dsid, tmp_path):
    dset = tmp_path / "ds"
    dset.mkdir()

    url_encoded = url_encode("file:///" + str(dset))

    d_token = client.get(
        f"/v1/datasets/{dsid}/urls/{url_encoded}/token").get_json()

    with patch("datalad_registry.dataset_urls._TOKEN_TTL", 0):
        r_post = client.post(f"/v1/datasets/{dsid}/urls", json=d_token)
    assert r_post.status_code == 410
    assert "message" in r_post.get_json()


def test_register_url_failed_verification(client, dsid, tmp_path):
    url_encoded = url_encode("file:///" + str(tmp_path))

    d_token = client.get(
        f"/v1/datasets/{dsid}/urls/{url_encoded}/token").get_json()
    r_post = client.post(f"/v1/datasets/{dsid}/urls", json=d_token)
    assert r_post.status_code == 202
    data = client.get(f"/v1/datasets/{dsid}/urls/{url_encoded}").get_json()
    assert data["status"] == "verification failed"
