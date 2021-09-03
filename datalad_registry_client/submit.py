import logging
from typing import Any
from typing import Dict
from typing import Optional
from typing import Iterator

import requests
from datalad.distribution.dataset import Dataset
from datalad.distribution.dataset import datasetmethod
from datalad.interface.base import build_doc
from datalad.interface.base import Interface
from datalad.interface.results import get_status_dict
from datalad.interface.utils import eval_results

from datalad_registry.utils import url_encode
from datalad_registry_client import opts


lgr = logging.getLogger("datalad.registry.submit")


@build_doc
class RegistrySubmit(Interface):
    """Submit a new URL for a dataset to a DataLad Registry instance.
    """

    _params_ = opts.common_params

    @staticmethod
    @datasetmethod(name="registry_submit")
    @eval_results
    def __call__(
            dataset: Optional[Dataset] = None,
            sibling: Optional[str] = None,
            url: Optional[str] = None,
            endpoint: Optional[str] = None
    ) -> Iterator[Dict[str, Any]]:
        # TODO: Allow recursive operation?
        options = opts.process_args(
            dataset=dataset, sibling=sibling, url=url, endpoint=endpoint)
        ds_id = options["ds_id"]
        urls = options.pop("urls")  # Don't include in res_base

        res_base = get_status_dict(action="registry-submit",
                                   logger=lgr, **options)

        base_url = f"{options['endpoint']}/datasets"

        for u in urls:
            url_encoded = url_encode(u)
            try:
                r_url = requests.get(
                    f"{base_url}/{ds_id}/urls/{url_encoded}",
                    timeout=1)
                r_url.raise_for_status()
            except requests.exceptions.RequestException as exc:
                yield dict(res_base, status="error", url=u,
                           message=("Check if URL is known failed: %s", exc))
                return
            url_info = r_url.json()
            if url_info.get("status") == "unknown":
                msg = "Registered URL"
            else:
                msg = "Announced update"

            try:
                r_patch = requests.patch(f"{base_url}/{ds_id}/urls/{url_encoded}",
                                         timeout=1)
                r_patch.raise_for_status()
            except requests.exceptions.RequestException as exc:
                yield dict(res_base, status="error", url=u,
                           message=("Submitting URL failed: %s", exc))
                return
            yield dict(res_base, status="ok", url=u,
                       message=("%s: %s", msg, u))
