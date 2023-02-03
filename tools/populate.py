# Warning: This script populates the running datalad-registry instance with selected
#          datasets from https://github.com/datalad/datalad-usage-dashboard/.

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

    id: StrictInt
    name: StrictStr
    url: HttpUrl
    status: Status


class GitHubRepo(Repo):
    """
    Pydantic model for representing GitHub repository information found in
    datalad-usage-dashboard
    """

    stars: StrictInt
    dataset: StrictBool
    run: StrictBool
    container_run: StrictBool


class OSFRepo(Repo):
    """
    Pydantic model for representing OSF repository information found in
    datalad-usage-dashboard
    """

    pass


# Establish a Pydantic model for representing dataset information obtain from
# the datalad-usage-dashboard repository

# Fetch dataset information from the datalad-usage-dashboard repository

# Submit dataset urls to the datalad-registry instance at once or sequentially
