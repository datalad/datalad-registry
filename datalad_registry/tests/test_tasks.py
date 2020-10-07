import time

from datalad_registry import tasks
from datalad_registry.models import Token


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
