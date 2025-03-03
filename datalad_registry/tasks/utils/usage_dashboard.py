# This file contains definitions for accessing information made available
# by the datalad-usage-dashboard, https://github.com/datalad/datalad-usage-dashboard.
import abc
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


class Repo(BaseModel, abc.ABC):
    """
    Pydantic model for representing a git repo represented
    in the datalad-usage-dashboard
    """

    name: StrictStr
    url: HttpUrl
    status: Status

    @property
    @abc.abstractmethod
    def clone_url(self) -> str:
        """
        The URL used for cloning the repo
        """
        pass


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

    @property
    def clone_url(self) -> str:
        return str(self.url) + ".git"


class OSFRepo(Repo):
    """
    Pydantic model for representing a git repo residing on OSF represented
    in the datalad-usage-dashboard
    """

    id: StrictStr

    @property
    def clone_url(self) -> str:
        raise NotImplementedError


class GinRepo(Repo):
    """
    Pydantic model for representing a git repo residing on GIN represented
    in the datalad-usage-dashboard
    """

    id: StrictInt
    stars: StrictInt

    @property
    def clone_url(self) -> str:
        return str(self.url)


class DataladHubRepo(GinRepo):
    """
    Pydantic model for representing a git repo residing on https://hub.datalad.org/
    represented in the datalad-usage-dashboard
    """

    # Note: The relationship of this model to the `GinRepo` is inspired by the
    # `RepoRecord` class in
    # https://github.com/datalad/datalad-usage-dashboard/blob/master/src/find_datalad_repos/record.py

    @property
    def clone_url(self) -> str:
        return str(self.url) + ".git"


class AtrisRepo(GinRepo):
    """
    Pydantic model for representing a git repo residing on https://atris.fz-juelich.de/
    represented in the datalad-usage-dashboard
    """

    # Note: The relationship of this model to the `GinRepo` is inspired by the
    # `RepoRecord` class in
    # https://github.com/datalad/datalad-usage-dashboard/blob/master/src/find_datalad_repos/record.py

    @property
    def clone_url(self) -> str:
        return str(self.url) + ".git"


class DashboardCollection(BaseModel):
    """
    Pydantic model for representing the collection of git repos represented
    in the datalad-usage-dashboard
    """

    github: list[GHRepo]
    osf: list[OSFRepo]
    gin: list[GinRepo]
    hub_datalad_org: list[DataladHubRepo]
    atris: list[AtrisRepo]
