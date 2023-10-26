import sys

import datalad

# The default base API endpoint of the DataLad Registry instance
# that the client interacts with.
DEFAULT_BASE_ENDPOINT = "http://127.0.0.1:5000/api/v2"

datalad.enable_librarymode()

command_suite = (
    "Interact with DataLad registry",
    [
        (
            "datalad_registry_client.submit_urls",
            "RegistrySubmitURLs",
            "registry-submit-urls",
            "registry_submit_urls",
        ),
        (
            "datalad_registry_client.get_urls",
            "RegistryGetURLs",
            "registry-get-urls",
            "registry_get_urls",
        ),
    ],
)

if sys.version_info[:2] < (3, 8):
    from importlib_metadata import version
else:
    from importlib.metadata import version

__version__ = version("datalad-registry")
