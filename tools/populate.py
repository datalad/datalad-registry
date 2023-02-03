# Warning: This script populates the running datalad-registry instance with selected
#          datasets from https://github.com/datalad/datalad-usage-dashboard/.

from typing import Optional

from pydantic import BaseModel, HttpUrl, StrictBool, StrictInt, StrictStr
import requests

from datalad_registry.utils import StrEnum

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


# Fetch git repo information from the datalad-usage-dashboard
resp = requests.get(DASHBOARD_COLLECTION_URL)
resp.raise_for_status()
dashboard_collection = DashboardCollection.parse_raw(resp.text)

# Obtain active GitHub repos
active_github_repos = [
    repo for repo in dashboard_collection.github if repo.status is Status.active
]

# Submit dataset urls to the datalad-registry instance at once or sequentially
