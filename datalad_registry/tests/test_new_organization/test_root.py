def test_root_redirect(flask_client):
    r_root = flask_client.get("/")
    assert r_root.status_code == 302
    assert r_root.headers["Location"].endswith("/overview/")
