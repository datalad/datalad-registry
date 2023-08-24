from pathlib import Path

import pytest

from datalad_registry.utils.pydantic_tls import path_must_be_absolute


class TestPathMustBeAbsolute:
    @pytest.mark.parametrize("path", [Path("/a/b"), Path("/a/b/c"), Path("/")])
    def test_absolute_path(self, path: Path):
        p = path_must_be_absolute(path)
        assert p == path

    @pytest.mark.parametrize("path", [Path("a/b"), Path("a/b/c"), Path("a")])
    def test_relative_path(self, path: Path):
        with pytest.raises(ValueError):
            path_must_be_absolute(path)
