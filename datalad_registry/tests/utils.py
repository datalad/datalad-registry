import uuid
from random import Random

random = Random()
random.seed("datalad-registry")


def make_dsid():
    """Generate a dataset ID like DataLad would.

    This is intended for lightweight tests that don't create
    full-fledged datasets.
    """
    return str(uuid.UUID(int=random.getrandbits(128)))
