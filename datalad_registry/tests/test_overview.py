from unittest.mock import patch

from datalad_registry.tests.utils import create_and_register_repos


def test_overview_pager(client, tmp_path):
    create_and_register_repos(client, tmp_path, 5)

    r_overview = client.get("/overview/")
    assert b"previous" not in r_overview.data
    assert b"next" not in r_overview.data

    with patch("datalad_registry.overview._PAGE_NITEMS", 2):
        r_overview_pg1 = client.get("/overview/")
        assert b"previous" not in r_overview_pg1.data
        assert b"next" in r_overview_pg1.data

        assert r_overview_pg1.data == client.get("/overview/?page=1").data

        r_overview_pg2 = client.get("/overview/?page=2")
        assert b"previous" in r_overview_pg2.data
        assert b"next" in r_overview_pg2.data

        r_overview_pg3 = client.get("/overview/?page=3")
        assert b"previous" in r_overview_pg3.data
        assert b"next" not in r_overview_pg3.data
