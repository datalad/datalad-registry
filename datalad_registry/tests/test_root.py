

def test_root_redirect(client):
    r_root = client.get("/")
    assert r_root.status_code == 302
    assert r_root.headers["Location"].endswith("/overview/")
