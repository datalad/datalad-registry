# This file contains definitions used as tools for the datalad_registry_client package.

from datalad import cfg

from . import DEFAULT_BASE_ENDPOINT


def get_base_endpoint() -> str:
    """
    :return: The value of the `datalad_registry.base_endpoint` option if set,
             or the value of `datalad_registry_client.DEFAULT_BASE_ENDPOINT` otherwise.
    """
    return cfg.get("datalad_registry.base_endpoint", DEFAULT_BASE_ENDPOINT)
