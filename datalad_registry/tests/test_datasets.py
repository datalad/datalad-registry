from unittest.mock import patch

from datalad_registry.utils import url_encode
from datalad_registry.tests.utils import init_repo_with_token
from datalad_registry.tests.utils import make_dsid


def test_datasets(client, tmp_path):
    dsids = []
    for idx in range(5):
        dsid = make_dsid()
        dset = tmp_path / f"ds{idx}"
        dset.mkdir()

        url = "file:///" + str(dset)
        url_encoded = url_encode(url)

        d_token = client.get(
            f"/v1/datasets/{dsid}/urls/{url_encoded}/token").get_json()

        init_repo_with_token(str(dset), d_token)

        r_post = client.post(f"/v1/datasets/{dsid}/urls", json=d_token)
        assert r_post.status_code == 202

        dsids.append(dsid)
    dsids = sorted(dsids)

    r_datasets = client.get("/v1/datasets").get_json()
    assert r_datasets["next"] is None
    assert r_datasets["previous"] is None
    assert dsids == r_datasets["dsids"]

    with patch("datalad_registry.datasets._PAGE_NITEMS", 3):
        r_datasets_pg1 = client.get("/v1/datasets").get_json()
        assert r_datasets_pg1["next"] == "/v1/datasets?page=2"
        assert r_datasets_pg1["previous"] is None
        assert dsids[:3] == r_datasets_pg1["dsids"]

        r_datasets_pg2 = client.get(r_datasets_pg1["next"]).get_json()
        assert r_datasets_pg2["next"] is None
        assert r_datasets_pg2["previous"] == "/v1/datasets?page=1"
        assert dsids[3:] == r_datasets_pg2["dsids"]
