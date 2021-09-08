import sys

command_suite = (
    "Interact with DataLad registry",
    [
        (
            "datalad_registry_client.submit",
            "RegistrySubmit",
            "registry-submit",
            "registry_submit",
        ),
        (
            "datalad_registry_client.submit_urls",
            "RegistrySubmitURLs",
            "registry-submit-urls",
            "registry_submit_urls",
        ),
    ],
)

if sys.version_info[:2] < (3, 8):
    from importlib_metadata import version
else:
    from importlib.metadata import version

__version__ = version("datalad-registry")
