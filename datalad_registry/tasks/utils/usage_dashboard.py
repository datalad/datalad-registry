# This file contains definitions for accessing information made available
# by the datalad-usage-dashboard, https://github.com/datalad/datalad-usage-dashboard.
from enum import auto

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
