import time

import pytest

from datalad_registry import tasks
from datalad_registry.models import Token
from datalad_registry.models import URL
from datalad_registry.utils import url_encode


def test_prune_old_tokens(app_instance, dsid):
    ts_now = int(time.time())
    ts_15days = ts_now - 1296000
    with app_instance.app.app_context():
        ses = app_instance.db.session
        assert ses.query(Token).count() == 0
        ses.add(Token(ts=ts_now, token="now-ish", dsid=dsid,
                      url="https://now-ish", status=0))
        ses.add(Token(ts=ts_15days, token="15-days-ago", dsid=dsid,
                      url="https://15-days-ago", status=0))
        ses.commit()

        assert ses.query(Token).count() == 2
        tasks.prune_old_tokens()
        assert [r.token for r in ses.query(Token)] == ["now-ish"]


def test_prune_old_tokens_explcit_cutoff(app_instance, dsid):
    with app_instance.app.app_context():
        ses = app_instance.db.session
        assert ses.query(Token).count() == 0

        ts = 1602083381
        for idx, token in enumerate("abcd"):
            ses.add(Token(ts=ts + idx, token=token, dsid=dsid,
                          url="https://" + token, status=0))
        ses.commit()

        assert ses.query(Token).count() == 4
        tasks.prune_old_tokens(ts + 2)
        assert [r.token for r in ses.query(Token)] == ["c", "d"]


def test_collect_git_info_empty(app_instance):
    with app_instance.app.app_context():
        tasks.collect_git_info()


def _register(ds, url, client):
    dsid = ds.id
    url_encoded = url_encode(url)
    d_token = client.get(
        f"/v1/datasets/{dsid}/urls/{url_encoded}/token").get_json()
    ds.repo.call_git(["update-ref", d_token["ref"], "HEAD"])
    client.post(f"/v1/datasets/{dsid}/urls", json=d_token)


@pytest.mark.slow
def test_collect_git_info(app_instance, tmp_path):
    import datalad.api as dl

    ds = dl.Dataset(tmp_path / "ds").create()
    ds.repo.call_git(["branch", "other"])
    ds.repo.call_git(["commit", "--allow-empty", "-mc1"])
    ds.repo.tag("v1")  # lightweight tag
    ds.repo.call_git(["commit", "--allow-empty", "-mc2"])
    ds.repo.call_git(["commit", "--allow-empty", "-mc3"])
    ds.repo.tag("v2", message="Version 2")

    url = "file:///" + ds.path
    _register(ds, url, app_instance.client)

    with app_instance.app.app_context():
        ses = app_instance.db.session
        res = ses.query(URL).filter_by(url=url).one()
        assert res.dsid == ds.id
        assert res.head is None

        tasks.collect_git_info()

        res = ses.query(URL).filter_by(url=url).one()
        assert res.head == ds.repo.get_hexsha()
        assert res.head_describe == "v2"
        branches = set(ln.split()[1] for ln in res.branches.splitlines())
        assert branches == set(ds.repo.get_branches())
        tags = set(ln.split()[1] for ln in res.tags.splitlines())
        assert tags == set(ds.repo.get_tags(output="name"))

        # collect_git_info() doesn't yet look at info_ts.  For now,
        # test a direct fetch by giving the URL explicitly.
        ds.repo.call_git(["commit", "--allow-empty", "-mc4"])
        ds.repo.tag("v3", message="Version 3")
        tasks.collect_git_info(urls=[url])
        res = ses.query(URL).filter_by(url=url).one()
        assert res.head == ds.repo.get_hexsha()
        assert res.head_describe == "v3"


@pytest.mark.slow
def test_collect_git_info_just_init(app_instance, tmp_path):
    import datalad.api as dl

    ds = dl.Dataset(tmp_path / "ds").create()
    url = "file:///" + ds.path
    _register(ds, url, app_instance.client)

    with app_instance.app.app_context():
        ses = app_instance.db.session
        res = ses.query(URL).filter_by(url=url).one()
        assert res.dsid == ds.id
        assert res.head is None

        tasks.collect_git_info()

        res = ses.query(URL).filter_by(url=url).one()
        assert res.head == ds.repo.get_hexsha()
        assert res.head_describe is None
        branches = set(ln.split()[1] for ln in res.branches.splitlines())
        assert branches == set(ds.repo.get_branches())
        assert not res.tags.strip()
