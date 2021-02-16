import subprocess as sp
import uuid
from random import Random

from datalad_registry.utils import url_encode

random = Random()
random.seed("datalad-registry")


def make_ds_id():
    """Generate a dataset ID like DataLad would.

    This is intended for lightweight tests that don't create
    full-fledged datasets.
    """
    return str(uuid.UUID(int=random.getrandbits(128)))


def init_repo_with_token(path, token_response):
    """Initialize empty repo with a challenge reference.

    This creates a minimal repository suitable for tests that don't
    need a proper dataset.

    Parameters
    ----------
    path : str
        Initialize repository at this location.
    token_response : dict
        A response from the token endpoint.  The value of its "ref"
        key is used as the challenge reference.
    """
    # Note: DataLad is intentionally avoided here.
    sp.run(["git", "init"], cwd=path)
    sp.run(["git", "commit", "--allow-empty", "-mc0"], cwd=path)
    sp.run(["git", "update-ref", token_response["ref"], "HEAD"], cwd=path)


def create_and_register_repos(client, path, n):
    """Create `n` empty repos under `path` and register URL with `client`.
    """
    records = []
    for idx in range(n):
        ds_id = make_ds_id()
        dset = path / f"ds{idx}"
        dset.mkdir()

        url = "file:///" + str(dset)
        url_encoded = url_encode(url)

        d_token = client.get(
            f"/v1/datasets/{ds_id}/urls/{url_encoded}/token").get_json()

        init_repo_with_token(str(dset), d_token)

        r_post = client.post(f"/v1/datasets/{ds_id}/urls", json=d_token)
        assert r_post.status_code == 202

        records.append({"ds_id": ds_id, "url_encoded": url_encoded})
    return records
