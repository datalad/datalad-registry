import logging

import requests

from datalad.distribution.dataset import datasetmethod
from datalad.interface.base import Interface
from datalad.interface.base import build_doc
from datalad.interface.results import get_status_dict
from datalad.interface.utils import eval_results

from datalad_registry_client import opts

lgr = logging.getLogger("datalad.registry.announce_update")


@build_doc
class RegistryAnnounceUpdate(Interface):
    """Announce that dataset accessible via URL has been updated.

    This maps to

      PATCH /datasets/{ds_id}/urls/{url_encoded}
    """

    _params_ = opts.common_params

    @staticmethod
    @datasetmethod(name="registry_announce_update")
    @eval_results
    def __call__(dataset=None, sibling=None, url=None, endpoint=None):
        # TODO: Allow recursive operation?
        options = opts.process_args(
            dataset=dataset, sibling=sibling, url=url, endpoint=endpoint)
        res_base = get_status_dict(action="registry-announce-update",
                                   logger=lgr, **options)

        base_url = f"{options['endpoint']}/datasets"
        try:
            resp = requests.patch(
                f"{base_url}/{options['ds_id']}/urls/{options['url_encoded']}",
                timeout=1)
            resp.raise_for_status()
        except requests.exceptions.RequestException as exc:
            yield dict(res_base, status="error",
                       message=("Announcing update failed: %s", exc))
            return
        assert resp.status_code == 202, "bug in response expectations"
        yield dict(res_base, status="ok", message="Announced update")
