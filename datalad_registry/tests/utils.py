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
    sp.run(["git", "init"], cwd=path)
    sp.run(["git", "commit", "--allow-empty", "-mc0"], cwd=path)
    sp.run(["git", "update-ref", token_response["ref"], "HEAD"], cwd=path)
