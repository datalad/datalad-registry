# This file contains simple miscellaneous definitions

from enum import Enum


class StrEnum(str, Enum):
    """
    A variation of Enum that is also a subclass of str, akin to IntEnum
    """

    @staticmethod
    def _generate_next_value_(name, start, count, last_values):  # noqa: U100 (unused)
        return name
