# This file specifies custom metadata extractors, for datalad_registry, and related
# definitions.
from collections.abc import Callable

from datalad_registry.models import RepoUrl, URLMetadata


def dlreg_dandiset_meta_extract(url: RepoUrl) -> URLMetadata:
    """
    Extract the metadata specified in the `dandiset.yaml` file of the DANDI dataset
    at a given URL

    :param url: The `RepoUrl` object representing the URL
                at which the dataset is located
    :return: A `URLMetadata` object containing the extracted metadata ready
             to be written (committed) to the database
    :raises FileNotFoundError: If the `dandiset.yaml` file is not found at the dataset

    Note: This function implements the `dandi:dandiset` extractor.
    """
    raise NotImplementedError


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
    """
    try:
        extractor_func = EXTRACTOR_MAP[extractor]
    except KeyError as e:
        raise ValueError(f"Extractor {extractor} not supported") from e
    else:
        return extractor_func(url)
