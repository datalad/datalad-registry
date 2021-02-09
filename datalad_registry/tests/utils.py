import subprocess as sp
import uuid
from random import Random

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
