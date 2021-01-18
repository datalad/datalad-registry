from unittest.mock import patch

from datalad_registry.utils import url_encode
from datalad_registry.tests.utils import init_repo_with_token
from datalad_registry.tests.utils import make_ds_id


def test_datasets(client, tmp_path):
    ds_ids = []
    for idx in range(5):
        ds_id = make_ds_id()
        dset = tmp_path / f"ds{idx}"
        dset.mkdir()

        url = "file:///" + str(dset)
        url_encoded = url_encode(url)

        d_token = client.get(
            f"/v1/datasets/{ds_id}/urls/{url_encoded}/token").get_json()

        init_repo_with_token(str(dset), d_token)

        r_post = client.post(f"/v1/datasets/{ds_id}/urls", json=d_token)
        assert r_post.status_code == 202

        ds_ids.append(ds_id)
    ds_ids = sorted(ds_ids)

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
