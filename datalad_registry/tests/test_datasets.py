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
    assert dsids == r_datasets["dsids"]
