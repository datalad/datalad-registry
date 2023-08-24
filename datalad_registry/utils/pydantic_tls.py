# Module for defining useful tools for use with Pydantic

from pathlib import Path


def path_must_be_absolute(p: Path) -> Path:
    """
    Pydantic validator for ensuring that a path is absolute
    :param p: The path to validate
    :return: The path if it is absolute
    :raises ValueError: If the path is not absolute
    """
    if not p.is_absolute():
        raise ValueError("Path must be absolute")
    return p
