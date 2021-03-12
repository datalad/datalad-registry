
import logging

import requests

from datalad.consts import PRE_INIT_COMMIT_SHA
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

    This handles the following steps:

      - Retrieve a challenge token for a URL that provides this
        dataset.  The URL may expose either the local repository or a
        sibling.

        GET /datasets/{dsid}/urls/{url_encoded}/token

      - Create a ref for the token in the local or sibling repository.

      - Register new URL.

        POST /datasets/{dsid}/urls
    """

    _params_ = opts.common_params

    @staticmethod
    @datasetmethod(name="registry_submit")
    @eval_results
    def __call__(dataset=None, sibling=None, url=None, endpoint=None):
        # TODO: Allow recursive operation?
        options = opts.process_args(
            dataset=dataset, sibling=sibling, url=url, endpoint=endpoint)
        ds = options["ds"]
        repo = ds.repo
        ds_id = options["ds_id"]

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

        # Get token.
        try:
            r_token = requests.get(
                f"{base_url}/{ds_id}/urls/{options['url_encoded']}/token",
                timeout=1)
            r_token.raise_for_status()
        except requests.exceptions.RequestException as exc:
            yield dict(res_base, status="error",
                       message=("Getting token failed: %s", exc))
            return

        # Add token ref.
        d_token = r_token.json()
        try:
            ref = d_token["ref"]
            token = d_token["token"]
        except KeyError as exc:
            yield dict(res_base, status="error",
                       message=("Invalid token response: %s", exc))
            return
        yield dict(res_base, status="ok", message="Retrieved token",
                   token=token, ref=ref)

        if sibling:
            repo.call_git(["push", sibling,
                           "{}:{}".format(PRE_INIT_COMMIT_SHA, ref)])
            ref_msg = ("Created token ref via push to %s", sibling)
        else:
            repo.update_ref(ref, PRE_INIT_COMMIT_SHA)
            ref_msg = "Created token ref"
        yield dict(res_base, status="ok", token=token, ref=ref,
                   message=ref_msg)

        # Register URL.
        try:
            r_post = requests.post(f"{base_url}/{ds_id}/urls",
                                   json=d_token, timeout=1)
            r_post.raise_for_status()
        except requests.exceptions.RequestException as exc:
            yield dict(res_base, status="error",
                       message=("Adding URL failed: %s", exc))
            return
        yield dict(res_base, status="ok",
                   location=r_post.headers["Location"],
                   message=("Registered URL: %s", options["url"]))
