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


def init_repo(path):
    """Initialize empty repo.

    This creates a minimal repository suitable for tests that don't
    need a proper dataset.

    Parameters
    ----------
    path : str
        Initialize repository at this location.
    """
    # Note: DataLad is intentionally avoided here.
    sp.run(["git", "init"], cwd=path)
    sp.run(["git", "commit", "--allow-empty", "-mc0"], cwd=path)


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

        init_repo(str(dset))

        r_patch = client.patch(f"/v1/datasets/{ds_id}/urls/{url_encoded}")
        assert r_patch.status_code == 202

        records.append({"ds_id": ds_id, "url_encoded": url_encoded})
    return records


def register_dataset(ds, url, client):
    """Register `url` for dataset `ds` with `client`.
    """
    ds_id = ds.id
    url_encoded = url_encode(url)
    client.patch(f"/v1/datasets/{ds_id}/urls/{url_encoded}")
