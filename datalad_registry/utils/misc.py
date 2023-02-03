# This file contains simple miscellaneous definitions

from enum import Enum


class StrEnum(str, Enum):
    """
    A variation of Enum that is also a subclass of str, akin to IntEnum
    """

    pass
