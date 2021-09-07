"""Common parameters and option handling.
"""

from typing import Any
from typing import Dict
from typing import Optional

from datalad.distribution.dataset import Dataset
from datalad.distribution.dataset import EnsureDataset
from datalad.distribution.dataset import require_dataset
from datalad.support.constraints import EnsureNone
from datalad.support.constraints import EnsureStr
from datalad.support.param import Parameter

from datalad_registry.utils import url_encode
from datalad_registry_client.consts import DEFAULT_ENDPOINT

common_params = dict(
    dataset=Parameter(
        args=("-d", "--dataset"),
        doc="""dataset to operate on.  If no dataset is given, an
        attempt is made to identify the dataset based on the current
        working directory.""",
        constraints=EnsureDataset() | EnsureNone()),
    endpoint=Parameter(
        args=("--endpoint",),
        metavar="URL",
        doc=f"""DataLad Registry instance to use (no trailing slash).
        This defaults to the datalad_registry.endpoint option, if set,
        or {DEFAULT_ENDPOINT} otherwise.""",
        constraints=EnsureStr() | EnsureNone()),
    sibling=Parameter(
        args=("-s", "--sibling",),
        metavar="NAME",
        doc="""name of the sibling accessible via the URL. If not
        given, the local dataset is assumed to be accessible via the
        URL specified with [CMD: --url CMD][PY: `url` PY].""",
        constraints=EnsureStr() | EnsureNone()),
    url=Parameter(
        args=("--url",),
        doc="""URL to register.  This option is required unless a
        sibling is specified, in which case remote.<name>.url is used
        by default.""",
        constraints=EnsureStr() | EnsureNone()))


def process_args(
        *, dataset: Optional[Dataset] = None,
        sibling: Optional[str] = None,
        url: Optional[str] = None,
        endpoint: Optional[str] = None
) -> Dict[str, Any]:
    """Process common arguments, returning dict with resolved/derived values.
    """
    ds = require_dataset(dataset, purpose="interact with a registry",
                         check_installed=True)
    repo = ds.repo
    ds_id = ds.id
    if not ds_id:
        raise ValueError("Dataset does not have datalad.dataset.id set: {}"
                         .format(ds.path))

    if sibling:
        remotes = repo.get_remotes()
        if sibling not in remotes:
            raise ValueError("Unknown sibling: {}".format(sibling))

    if not url:
        if not sibling:
            raise ValueError(
                "Must specify URL to use when sibling isn't given")
        url = repo.config.get("remote.{}.url".format(sibling))
        if not url:
            raise ValueError("Could not find URL for {}".format(sibling))

    endpoint = endpoint or repo.config.get(
        "datalad_registry.endpoint",
        DEFAULT_ENDPOINT)
    return dict(ds=ds, ds_id=ds_id,
                sibling=sibling, url=url, url_encoded=url_encode(url),
                endpoint=endpoint)
