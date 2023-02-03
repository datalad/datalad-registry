# Warning: This script populates the running datalad-registry instance with selected
#          datasets from https://github.com/datalad/datalad-usage-dashboard/.

from typing import Optional

from pydantic import BaseModel, HttpUrl, StrictBool, StrictInt, StrictStr

from datalad_registry.utils import StrEnum


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


# Establish a Pydantic model for representing dataset information obtain from
# the datalad-usage-dashboard repository

# Fetch dataset information from the datalad-usage-dashboard repository

# Submit dataset urls to the datalad-registry instance at once or sequentially
