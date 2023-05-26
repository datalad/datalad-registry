from pathlib import Path


def cache_path_trans(cache_path: Path) -> str:
    """
    Transform a cache path to its string representation. If the cache path is absolute,
    only the last three components of the path are used in the string representation.
    """
    if cache_path.is_absolute():
        cache_path = Path(*(cache_path.parts[-3:]))
    return str(cache_path)
