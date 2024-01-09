# This file contains definitions for accessing information made available
# by the datalad-usage-dashboard, https://github.com/datalad/datalad-usage-dashboard.
from enum import auto
from typing import Optional

from pydantic import BaseModel, HttpUrl, StrictInt, StrictStr

from datalad_registry.utils import StrEnum

# URL of the JSON representation of all the repositories in the datalad-usage-dashboard
DASHBOARD_COLLECTION_URL = (
    "https://raw.githubusercontent.com/datalad/"
    "datalad-usage-dashboard/master/datalad-repos.json"
)


class Status(StrEnum):
    """
    Enum for representing the status of repo
    """

    active = auto()
    gone = auto()


class Repo(BaseModel):
    """
    Pydantic model for representing a git repo represented
    in the datalad-usage-dashboard
    """

    name: StrictStr
    url: HttpUrl
    status: Status


class GHRepo(Repo):
    """
    Pydantic model for representing a git repo residing on GitHub represented
    in the datalad-usage-dashboard
    """

    id: Optional[StrictInt]
    stars: StrictInt
    dataset: bool
    run: bool
    container_run: bool


class OSFRepo(Repo):
    """
    Pydantic model for representing a git repo residing on OSF represented
    in the datalad-usage-dashboard
    """

    id: StrictStr


class GinRepo(Repo):
    """
    Pydantic model for representing a git repo residing on GIN represented
    in the datalad-usage-dashboard
    """

    id: StrictInt
    stars: StrictInt


class DashboardCollection(BaseModel):
    """
    Pydantic model for representing the collection of git repos represented
    in the datalad-usage-dashboard
    """

    github: list[GHRepo]
    osf: list[OSFRepo]
    gin: list[GinRepo]
