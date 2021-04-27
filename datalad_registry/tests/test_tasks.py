import pytest

from datalad_registry import tasks
from datalad_registry.models import URL
from datalad_registry.tests.utils import register_dataset
from datalad_registry.utils import url_encode


@pytest.mark.slow
def test_collect_dataset_info_empty(app_instance):
    with app_instance.app.app_context():
        tasks.collect_dataset_info()


@pytest.mark.slow
def test_collect_dataset_info(app_instance, tmp_path):
    import datalad.api as dl

    ds = dl.Dataset(tmp_path / "ds").create()
    repo = ds.repo
    repo.call_git(["branch", "other"])
    repo.call_git(["commit", "--allow-empty", "-mc1"])
    repo.tag("v1")  # lightweight tag
    repo.call_git(["commit", "--allow-empty", "-mc2"])
    repo.call_git(["commit", "--allow-empty", "-mc3"])
    repo.tag("v2", message="Version 2")

    url = "file:///" + ds.path
    register_dataset(ds, url, app_instance.client)

    with app_instance.app.app_context():
        ses = app_instance.db.session
        res = ses.query(URL).filter_by(url=url).one()
        assert res.ds_id == ds.id
        assert res.head is None

        tasks.collect_dataset_info()

        res = ses.query(URL).filter_by(url=url).one()
        assert res.head == repo.get_hexsha()
        assert res.head_describe == "v2"
        assert res.annex_uuid == repo.uuid
        branches = set(ln.split()[1] for ln in res.branches.splitlines())
        assert branches == set(repo.get_branches()) | {"HEAD"}
        tags = set(ln.split()[1] for ln in res.tags.splitlines())
        assert tags == set(repo.get_tags(output="name"))

        # collect_dataset_info() doesn't yet look at info_ts.  For
        # now, test a direct fetch by giving the URL explicitly.
        repo.call_git(["commit", "--allow-empty", "-mc4"])
        repo.tag("v3", message="Version 3")
        tasks.collect_dataset_info(urls=[url])
        res = ses.query(URL).filter_by(url=url).one()
        assert res.head == repo.get_hexsha()
        assert res.head_describe == "v3"


@pytest.mark.slow
def test_collect_dataset_info_just_init(app_instance, tmp_path):
    import datalad.api as dl

    ds = dl.Dataset(tmp_path / "ds").create()
    repo = ds.repo
    url = "file:///" + ds.path
    register_dataset(ds, url, app_instance.client)

    with app_instance.app.app_context():
        ses = app_instance.db.session
        res = ses.query(URL).filter_by(url=url).one()
        assert res.ds_id == ds.id
        assert res.head is None

        tasks.collect_dataset_info()

        res = ses.query(URL).filter_by(url=url).one()
        assert res.head == repo.get_hexsha()
        assert res.head_describe is None
        assert res.annex_uuid == repo.uuid
        branches = set(ln.split()[1] for ln in res.branches.splitlines())
        assert branches == set(repo.get_branches()) | {"HEAD"}
        assert not res.tags.strip()


@pytest.mark.slow
def test_collect_dataset_info_no_annex(app_instance, tmp_path):
    import datalad.api as dl

    ds = dl.Dataset(tmp_path / "ds").create(annex=False)
    repo = ds.repo
    url = "file:///" + ds.path
    register_dataset(ds, url, app_instance.client)

    with app_instance.app.app_context():
        ses = app_instance.db.session
        res = ses.query(URL).filter_by(url=url).one()
        assert res.ds_id == ds.id
        assert res.head is None

        tasks.collect_dataset_info()

        res = ses.query(URL).filter_by(url=url).one()
        assert res.head == repo.get_hexsha()
        assert res.annex_uuid is None
        assert res.annex_key_count is None


@pytest.mark.slow
def test_collect_dataset_info_announced_update(app_instance, tmp_path):
    import datalad.api as dl

    ds = dl.Dataset(tmp_path / "ds").create()
    (ds.pathobj / "foo").write_text("foo")
    ds.save()

    repo = ds.repo
    repo.tag("v1")

    url = "file:///" + ds.path
    register_dataset(ds, url, app_instance.client)

    with app_instance.app.app_context():
        ses = app_instance.db.session
        tasks.collect_dataset_info()
        res = ses.query(URL).filter_by(url=url).one()
        assert res.head == repo.get_hexsha()
        assert res.head_describe == "v1"
        assert res.annex_uuid == repo.uuid
        assert res.annex_key_count == 1

        (ds.pathobj / "bar").write_text("bar")
        ds.save()
        repo.tag("v2", message="Version 2")

        url_encoded = url_encode(url)
        app_instance.client.patch(f"/v1/datasets/{ds.id}/urls/{url_encoded}")
        tasks.collect_dataset_info()
        res = ses.query(URL).filter_by(url=url).one()
        head = repo.get_hexsha()
        assert res.head == head
        assert res.head_describe == "v2"
        assert res.annex_key_count == 2

        info = app_instance.client.get(
            f"/v1/datasets/{ds.id}/urls/{url_encoded}").get_json()["info"]
        assert info["head"] == head
        assert info["head_describe"] == "v2"
        assert info["annex_key_count"] == 2
