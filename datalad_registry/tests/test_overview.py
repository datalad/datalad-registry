import re
import time
from unittest.mock import patch

import pytest

from datalad_registry.tests.utils import create_and_register_repos
from datalad_registry.tests.utils import register_dataset


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


@pytest.mark.slow
def test_overview_sort(client, tmp_path):
    import datalad.api as dl
    from datalad_registry import tasks

    for name in ["ds1", "ds2", "ds3"]:
        ds = dl.Dataset(tmp_path / name).create()
        if name == "ds1":
            repo = ds.repo
            repo.tag("v1", message="Version 2")
            repo.call_git(["commit", "--allow-empty", "-mc1"])
        else:
            (ds.pathobj / "foo").write_text("foo")
            if name == "ds2":
                (ds.pathobj / "bar").write_text("bar")
            ds.save()
        url = "file:///" + ds.path
        register_dataset(ds, url, client)
        tasks.collect_dataset_info()
        time.sleep(0.01)

    def assert_ds_order(order, output):
        match = re.finditer(b'/(ds[123])</td>', output)
        assert match, "regexp unexpectedly didn't match"
        assert [x.group(1) for x in match] == order

    # By default, most recently updated comes first.
    r_default = client.get("/overview/")
    assert_ds_order([b"ds3", b"ds2", b"ds1"], r_default.data)

    assert r_default.data == client.get("/overview/?sort=update-desc").data

    r_update_asc = client.get("/overview/?sort=update-asc")
    assert_ds_order([b"ds1", b"ds2", b"ds3"], r_update_asc.data)

    r_keys_asc = client.get("/overview/?sort=keys-asc")
    assert_ds_order([b"ds1", b"ds3", b"ds2"], r_keys_asc.data)

    r_keys_desc = client.get("/overview/?sort=keys-desc")
    assert_ds_order([b"ds2", b"ds3", b"ds1"], r_keys_desc.data)

    r_url_desc = client.get("/overview/?sort=url-desc")
    assert_ds_order([b"ds3", b"ds2", b"ds1"], r_url_desc.data)

    r_url_asc = client.get("/overview/?sort=url-asc")
    assert_ds_order([b"ds1", b"ds2", b"ds3"], r_url_asc.data)

    # Unknown falls back to default.
    assert r_default.data == client.get("/overview/?sort=unknown").data


@pytest.mark.slow
def test_overview_filter(client, tmp_path):
    import datalad.api as dl
    from datalad_registry import tasks

    for name in ["foo", "foobar", "baz"]:
        ds = dl.Dataset(tmp_path / name).create()
        url = "file:///" + ds.path
        register_dataset(ds, url, client)
        tasks.collect_dataset_info()

    r_no_filter = client.get("/overview/")
    for name in [b"foo", b"foobar", b"baz"]:
        assert name in r_no_filter.data

    r_ba_filter = client.get("/overview/?filter=ba")
    for name in [b"foobar", b"baz"]:
        assert name in r_ba_filter.data
    assert b"foo</td>" not in r_ba_filter.data

    r_foo_filter = client.get("/overview/?filter=foo")
    for name in [b"foo", b"foobar"]:
        assert name in r_foo_filter.data
    assert b"baz" not in r_foo_filter.data
