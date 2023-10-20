# This file specifies custom metadata extractors, for datalad_registry, and related
# definitions.
from collections.abc import Callable

from datalad.distribution.dataset import require_dataset
from yaml import load as yaml_load

try:
    # Import the C-based YAML loader if available
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    # Otherwise, import the Python-based YAML loader
    from yaml import SafeLoader  # type: ignore

from datalad_registry.models import RepoUrl, URLMetadata
from datalad_registry.utils.datalad_tls import get_head_describe


class InvalidRequiredFileError(Exception):
    """
    Raised when a required file fails to meet the requirements
    for the metadata extraction
    """

    pass


def dlreg_dandiset_meta_extract(url: RepoUrl) -> URLMetadata:
    """
    Extract the metadata specified in the `dandiset.yaml` file of the DANDI dataset
    at a given URL

    :param url: The `RepoUrl` object representing the URL
                at which the dataset is located
    :return: A `URLMetadata` object containing the extracted metadata ready
             to be written (committed) to the database
    :raises FileNotFoundError: If the `dandiset.yaml` file is not found at the dataset
    :raises InvalidRequiredFileError: If the `dandiset.yaml` file has no document

    Note: This function implements the `dandi:dandiset` extractor.
    Note: This function is meant to be called inside a Celery task for it requires
          an active application context of the Flask app
    Note: This function must be called with a RepoUrl object with a cache path, i.e.,
          one that must have been processed already.
    """
    name = "dandi:dandiset"  # Name of this extractor
    version = "0.0.1"  # Version of this extractor

    assert url.cache_path_abs is not None, (
        f"Encountered a RepoUrl with no cache path, "
        f"with a processed flag set to {url.processed}"
    )

    with open(url.cache_path_abs / "dandiset.yaml", "rb") as f:
        extracted_metadata = yaml_load(f, Loader=SafeLoader)

    if extracted_metadata is None:
        raise InvalidRequiredFileError("dandiset.yaml has no document.")

    ds = require_dataset(
        url.cache_path_abs, check_installed=True, purpose="dandiset metadata extraction"
    )

    return URLMetadata(
        dataset_describe=get_head_describe(ds),
        dataset_version=ds.repo.get_hexsha(),
        extractor_name=name,
        extractor_version=version,
        extraction_parameter={},
        extracted_metadata=extracted_metadata,
        url=url,
    )


def dlreg_dandi_assets_meta_extract(url: RepoUrl) -> URLMetadata:
    """
    Extract the metadata specified in the `.dandi/assets.json` file of the DANDI dataset
    at a given URL

    :param url: The `RepoUrl` object representing the URL
    :return: A `URLMetadata` object containing the extracted metadata ready
    :raises FileNotFoundError: If the `.dandi/assets.json` file is not found
                               at the dataset

    Note: This function implements the `dandi:assets` extractor.
    """
    raise NotImplementedError


# A mapping from the names of the supported extractors to the functions
# that implement those extractors respectively
EXTRACTOR_MAP: dict[str, Callable[[RepoUrl], URLMetadata]] = {
    "dandi:dandiset": dlreg_dandiset_meta_extract,
    "dandi:assets": dlreg_dandi_assets_meta_extract,
}


def dlreg_meta_extract(extractor: str, url: RepoUrl) -> URLMetadata:
    """
    Extract metadata from the dataset at a given URL using the specified extractor.

    :param extractor: The name of the extractor to use
    :param url: The `RepoUrl` object representing the URL
                at which the dataset is located
    :return: A `URLMetadata` object containing the extracted metadata ready
             to be written (committed) to the database
    :raises ValueError: If the argument for `extractor` is not one of the extractors
                        specified in `SUPPORTED_EXTRACTORS`

    Note: This function is meant to be called inside a Celery task for it requires
          an active application context of the Flask app
    """
    try:
        extractor_func = EXTRACTOR_MAP[extractor]
    except KeyError as e:
        raise ValueError(f"Extractor {extractor} is not supported") from e
    else:
        return extractor_func(url)
