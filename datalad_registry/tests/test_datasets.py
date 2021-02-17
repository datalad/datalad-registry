from unittest.mock import patch

from datalad_registry.tests.utils import create_and_register_repos


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
