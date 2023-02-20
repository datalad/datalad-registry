# Warning: This script populates the running datalad-registry instance with selected
#          datasets from https://github.com/datalad/datalad-usage-dashboard/.

# Note: Currently, this script can only populate the datalad-registry instance with
#       active datasets on GitHub listed in datalad-usage-dashboard.

from typing import Optional

import click
from pydantic import BaseModel, HttpUrl, StrictBool, StrictInt, StrictStr
import requests

from datalad_registry.utils import StrEnum
from datalad_registry_client.submit_urls import RegistrySubmitURLs

DASHBOARD_COLLECTION_URL = (
    "https://github.com/datalad/datalad-usage-dashboard/raw/master/datalad-repos.json"
)


class Status(StrEnum):
    """
    Enum for representing the status of repo
    """

    active = "active"
    gone = "gone"


class Repo(BaseModel):
    """
    Pydantic model for representing a git repo found in datalad-usage-dashboard
    """

    name: StrictStr
    url: HttpUrl
    status: Status


class GitHubRepo(Repo):
    """
    Pydantic model for representing GitHub repository information found in
    datalad-usage-dashboard
    """

    id: Optional[StrictInt]
    stars: StrictInt
    dataset: StrictBool
    run: StrictBool
    container_run: StrictBool


class OSFRepo(Repo):
    """
    Pydantic model for representing OSF repository information found in
    datalad-usage-dashboard
    """

    id: StrictStr


class DashboardCollection(BaseModel):
    """
    Pydantic model for representing a collection of git repos found in
    datalad-usage-dashboard
    """

    github: list[GitHubRepo]
    osf: list[OSFRepo]


@click.command()
@click.option(
    "--start", type=int, default=None, help="The index of the first dataset to populate"
)
@click.option(
    "--stop",
    type=int,
    default=None,
    help="One past the index of the last dataset to populate",
)
def populate(start: Optional[int], stop: Optional[int]) -> None:
    """
    Populate the running datalad-registry instance with selected datasets from
    the datalad-usage-dashboard
    """
    # Fetch git repo information from the datalad-usage-dashboard
    resp = requests.get(DASHBOARD_COLLECTION_URL)
    resp.raise_for_status()
    dashboard_collection = DashboardCollection.parse_raw(resp.text)

    # Obtain active GitHub datasets from the listing in datalad-usage-dashboard
    active_github_datasets = [
        repo
        for repo in dashboard_collection.github
        if repo.status is Status.active and repo.dataset
    ]

    # Build clone URLs for active GitHub datasets
    active_github_dataset_urls = [ds.url + ".git" for ds in active_github_datasets]

    # Select URLs of active GitHub datasets to submit
    s = slice(start, stop)
    selected_dataset_urls = active_github_dataset_urls[s]

    click.echo(
        f"Submitting {len(selected_dataset_urls)} of the total "
        f"{len(active_github_dataset_urls)} active GitHub datasets "
        f"to the datalad-registry."
    )

    # Submit selected URLs of active GitHub datasets to the datalad-registry
    registry_submit_urls = RegistrySubmitURLs()
    registry_submit_urls(selected_dataset_urls)


if __name__ == "__main__":
    populate()
