
import logging

import requests

from datalad.distribution.dataset import datasetmethod

from datalad.interface.base import Interface
from datalad.interface.base import build_doc
from datalad.interface.results import get_status_dict
from datalad.interface.utils import eval_results

from datalad_registry_client import opts

lgr = logging.getLogger("datalad.registry.submit")


@build_doc
class RegistrySubmit(Interface):
    """Submit a new URL to a DataLad Registry instance.
    """

    _params_ = opts.common_params

    @staticmethod
    @datasetmethod(name="registry_submit")
    @eval_results
    def __call__(dataset=None, sibling=None, url=None, endpoint=None):
        # TODO: Allow recursive operation?
        options = opts.process_args(
            dataset=dataset, sibling=sibling, url=url, endpoint=endpoint)
        ds_id = options["ds_id"]
        url = options["url"]

        res_base = get_status_dict(action="registry-submit",
                                   logger=lgr, **options)

        base_url = f"{options['endpoint']}/datasets"

        try:
            r_url = requests.get(
                f"{base_url}/{ds_id}/urls/{options['url_encoded']}",
                timeout=1)
            r_url.raise_for_status()
        except requests.exceptions.RequestException as exc:
            yield dict(res_base, status="error",
                       message=("Check if URL is known failed: %s", exc))
            return
        url_info = r_url.json()
        if url_info.get("status") != "unknown":
            yield dict(res_base, status="notneeded",
                       message="URL already known to registry")
            return

        # Register URL.
        try:
            r_post = requests.post(f"{base_url}/{ds_id}/urls",
                                   json={"url": url}, timeout=1)
            r_post.raise_for_status()
        except requests.exceptions.RequestException as exc:
            yield dict(res_base, status="error",
                       message=("Adding URL failed: %s", exc))
            return
        yield dict(res_base, status="ok",
                   location=r_post.headers["Location"],
                   message=("Registered URL: %s", options["url"]))
