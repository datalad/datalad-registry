from unittest.mock import patch

from datalad_registry.tests.utils import create_and_register_repos
from datalad_registry.tests.utils import init_repo
from datalad_registry.utils import url_encode


def test_datasets(client, tmp_path):
    repos = create_and_register_repos(client, tmp_path, 5)
    ds_ids = sorted(r["ds_id"] for r in repos)

    r_datasets = client.get("/v1/datasets").get_json()
    assert r_datasets["next"] is None
    assert r_datasets["previous"] is None
    assert ds_ids == r_datasets["ds_ids"]

    with patch("datalad_registry.datasets._PAGE_NITEMS", 3):
        r_datasets_pg1 = client.get("/v1/datasets").get_json()
        assert r_datasets_pg1["next"] == "/v1/datasets?page=2"
        assert r_datasets_pg1["previous"] is None
        assert ds_ids[:3] == r_datasets_pg1["ds_ids"]

        r_datasets_pg2 = client.get(r_datasets_pg1["next"]).get_json()
        assert r_datasets_pg2["next"] is None
        assert r_datasets_pg2["previous"] == "/v1/datasets?page=1"
        assert ds_ids[3:] == r_datasets_pg2["ds_ids"]


def test_urls(client, tmp_path):
    from datalad.api import Dataset

    dset = tmp_path / "ds"
    ds = Dataset(dset)
    ds.create()
    ds_id = ds.id

    url = "file:///" + str(dset)
    url_encoded = url_encode(url)

    def get_status():
        response = client.get(f"/v1/urls/{url_encoded}")
        return response.get_json()["status"]

    def get_status_with_id():
        response = client.get(f"/v1/datasets/{ds_id}/urls/{url_encoded}")
        return response.get_json()["status"]

    assert get_status() == "unknown"
    assert get_status_with_id() == "unknown"

    init_repo(str(dset))

    r_patch = client.patch(f"/v1/urls/{url_encoded}")
    assert r_patch.status_code == 202

    urls = client.get(f"/v1/datasets/{ds_id}/urls").get_json()["urls"]
    assert urls == [url]
    assert get_status() == "known"
    assert get_status_with_id() == "known"

    # And again.
    r_patch2 = client.patch(f"/v1/urls/{url_encoded}")
    assert r_patch2.status_code == 202
    assert get_status() == "known"
    assert get_status_with_id() == "known"
