import os
from pathlib import Path
from uuid import UUID

import datalad.api as dl
from datalad.api import Dataset
import pytest

from datalad_registry.utils.datalad_tls import (
    WtAnnexedFileInfo,
    clone,
    ensure_preferred_branch_checked_out,
    get_origin_annex_key_count,
    get_origin_annex_uuid,
    get_origin_branches,
    get_origin_default_branch,
    get_origin_upstream_branch,
    get_wt_annexed_file_info,
    pick_preferred_branch,
)

_TEST_MIN_DATASET_URL = "https://github.com/datalad/testrepo--minimalds.git"
_TEST_MIN_DATASET_ID = "e7f3d914-e971-11e8-a371-f0d5bf7b5561"


class TestClone:
    @pytest.mark.parametrize(
        "return_type",
        ["generator", "list", "item-or-list"],
    )
    def test_unsupported_kwarg(self, tmp_path, return_type):
        """
        Test the case that the unsupported keyword argument of `return_type`
        is provided
        """
        with pytest.raises(TypeError):
            clone(source=_TEST_MIN_DATASET_URL, path=tmp_path, return_type=return_type)

    @pytest.mark.parametrize(
        "clone_return",
        [None, list(), ["a", "b", "c"]],
    )
    def test_no_dataset_object_produced(self, monkeypatch, tmp_path, clone_return):
        """
        Test the case that no `datalad.api.Dataset` object is produced after
        a successful run of the underlying `datalad.api.clone` function
        """
        from datalad import api as dl

        # noinspection PyUnusedLocal
        def mock_clone(*args, **kwargs):  # noqa: U100 (unused argument)
            return clone_return

        monkeypatch.setattr(dl, "clone", mock_clone)

        with pytest.raises(RuntimeError):
            clone(source=_TEST_MIN_DATASET_URL, path=tmp_path)

    def test_clone_minimal_dataset(self, tmp_path):
        """
        Test cloning a minimal dataset used for testing
        """
        ds = clone(source=_TEST_MIN_DATASET_URL, path=tmp_path)
        assert ds.id == _TEST_MIN_DATASET_ID


class TestGetOriginAnnexUuid:
    @pytest.mark.parametrize("ds_name", ["empty_ds_annex", "two_files_ds_annex"])
    def test_annex_repo(self, ds_name, request, tmp_path):
        """
        Test the case that the origin remote is a git-annex repo
        """
        ds = request.getfixturevalue(ds_name)
        ds_clone = clone(source=ds.path, path=tmp_path)
        assert get_origin_annex_uuid(ds_clone) == UUID(ds.config.get("annex.uuid"))

    @pytest.mark.parametrize(
        "ds_name", ["empty_ds_non_annex", "two_files_ds_non_annex"]
    )
    def test_non_annex_repo(self, ds_name, request, tmp_path):
        """
        Test the case that the origin remote is not a git-annex repo
        """
        ds = request.getfixturevalue(ds_name)
        ds_clone = clone(source=ds.path, path=tmp_path)
        assert get_origin_annex_uuid(ds_clone) is None

    def test_origin_annex_uuid_not_exist(self, tmp_path):
        """
        Test the case that the origin remote has no annex UUID even though it is an
        annex repo
        """
        ds = clone(source=_TEST_MIN_DATASET_URL, path=tmp_path)
        assert get_origin_annex_uuid(ds) is None


class TestGetOriginAnnexKeyCount:
    @pytest.mark.parametrize(
        "ds_name, expected_annex_key_count",
        [("empty_ds_annex", 0), ("two_files_ds_annex", 2)],
    )
    def test_annex_repo(self, ds_name, expected_annex_key_count, request, tmp_path):
        """
        Test the case that the origin remote is a git-annex repo
        """
        ds = request.getfixturevalue(ds_name)
        ds_clone = clone(source=ds.path, path=tmp_path)
        annex_key_count = get_origin_annex_key_count(ds_clone)
        assert type(annex_key_count) is int
        assert annex_key_count == expected_annex_key_count

    @pytest.mark.parametrize(
        "ds_name", ["empty_ds_non_annex", "two_files_ds_non_annex"]
    )
    def test_non_annex_repo(self, ds_name, request, tmp_path):
        """
        Test the case that the origin remote is not a git-annex repo
        """
        ds = request.getfixturevalue(ds_name)
        ds_clone = clone(source=ds.path, path=tmp_path)
        assert get_origin_annex_key_count(ds_clone) is None


class TestGetWtAnnexedFileInfo:
    @pytest.mark.parametrize(
        "ds_name, expected_info",
        [
            ("empty_ds_annex", WtAnnexedFileInfo(0, 0)),
            ("two_files_ds_annex", WtAnnexedFileInfo(2, 38)),
        ],
    )
    def test_annex_repo(self, ds_name, expected_info, request):
        """
        Test the case that the given dataset is a git-annex repo
        """
        ds = request.getfixturevalue(ds_name)
        wt_annexed_file_info = get_wt_annexed_file_info(ds)
        assert wt_annexed_file_info == expected_info

    @pytest.mark.parametrize(
        "ds_name", ["empty_ds_non_annex", "two_files_ds_non_annex"]
    )
    def test_non_annex_repo(self, ds_name, request):
        """
        Test the case that the given dataset is not a git-annex repo
        """
        ds = request.getfixturevalue(ds_name)
        assert get_wt_annexed_file_info(ds) is None


@pytest.mark.parametrize(
    "ds_name",
    [
        "empty_ds_annex",
        "two_files_ds_annex",
        "empty_ds_non_annex",
        "two_files_ds_non_annex",
    ],
)
def test_get_origin_branches(ds_name, request, tmp_path):
    ds: Dataset = request.getfixturevalue(ds_name)
    ds_clone = clone(source=ds.path, path=tmp_path)

    origin_branches = get_origin_branches(ds_clone)

    branch_names = set(ds.repo.get_branches())

    assert set(origin_branches) == branch_names

    for o_b_name, o_b_data in origin_branches.items():
        assert o_b_data == {
            "hexsha": ds.repo.get_hexsha(o_b_name),
            "last_commit_dt": ds.repo.call_git(
                ["log", "-1", "--format=%aI", o_b_name]
            ).strip(),
        }


def _mock_no_match_re_search(*_args, **_kwargs):
    return None


def _two_level_clone(ds: Dataset, dir_path: Path) -> tuple[Dataset, Dataset]:
    """
    Do a two-level clone of a given dataset within a given directory

    :param ds: The given directory
    :param dir_path: The given directory, which must be empty
    :return: A tuple consisting of the first and second level clones
             of the given dataset each residing in a subdirectory of the given directory
    """
    l1_clone_path = dir_path / "l1_clone"
    l2_clone_path = dir_path / "l2_clone"

    l1_clone = clone(source=ds.path, path=l1_clone_path)
    l2_clone = clone(source=l1_clone.path, path=l2_clone_path)

    return l1_clone, l2_clone


class TestGetOriginDefaultBranch:
    def test_no_match(self, two_files_ds_non_annex, tmp_path, monkeypatch):
        """
        Test the case that the default branch name of the origin remote of the given
        dataset can't be extracted from the output of `git ls-remote`
        """

        ds_clone = clone(source=two_files_ds_non_annex.path, path=tmp_path)

        with pytest.raises(RuntimeError, match="Failed to extract the name"):
            with monkeypatch.context() as m:
                import re

                m.setattr(re, "search", _mock_no_match_re_search)
                get_origin_default_branch(ds_clone)

    @pytest.mark.parametrize(
        "ds_name",
        [
            "empty_ds_annex",
            "two_files_ds_annex",
            "empty_ds_non_annex",
            "two_files_ds_non_annex",
        ],
    )
    @pytest.mark.parametrize("branch_name", ["foo", "bar"])
    def test_normal_operation(self, ds_name, branch_name, request, tmp_path):
        """
        Test the normal operation of `get_origin_default_branch`
        """
        ds: Dataset = request.getfixturevalue(ds_name)

        l1_clone, l2_clone = _two_level_clone(ds, tmp_path)

        l1_clone.repo.call_git(["checkout", "-b", branch_name])

        assert get_origin_default_branch(l2_clone) == branch_name


class TestGetOriginUpstreamBranch:
    def test_no_match(self, two_files_ds_non_annex, tmp_path, monkeypatch):
        """
        Test the case that the name of the upstream branch at the origin remote of
        the current local branch of a given dataset can't be extracted from the output
        of `git rev-parse`
        """

        ds_clone = clone(source=two_files_ds_non_annex.path, path=tmp_path)

        with pytest.raises(RuntimeError, match="Failed to extract the name"):
            with monkeypatch.context() as m:
                import re

                m.setattr(re, "search", _mock_no_match_re_search)
                get_origin_upstream_branch(ds_clone)

    @pytest.mark.parametrize(
        "ds_name",
        [
            "empty_ds_annex",
            "two_files_ds_annex",
            "empty_ds_non_annex",
            "two_files_ds_non_annex",
        ],
    )
    @pytest.mark.parametrize("branch_name", ["foo", "bar"])
    def test_normal_operation(self, ds_name, branch_name, request, tmp_path):
        """
        Test the normal operation of `get_origin_upstream_branch`
        """
        ds: Dataset = request.getfixturevalue(ds_name)

        _, l2_clone = _two_level_clone(ds, tmp_path)

        l2_clone.repo.call_git(["checkout", "-b", branch_name])
        l2_clone.repo.call_git(["push", "-u", "origin", branch_name])

        assert get_origin_upstream_branch(l2_clone) == branch_name


def _commit_at(ds: Dataset, filename: str, iso_date: str) -> str:
    """Add and commit `filename` with a controlled author/committer date."""
    (Path(ds.path) / filename).write_text(f"content of {filename}\n")
    env = {
        **os.environ,
        "GIT_AUTHOR_DATE": iso_date,
        "GIT_COMMITTER_DATE": iso_date,
    }
    ds.repo.call_git(["add", filename], env=env)
    ds.repo.call_git(["commit", "-m", f"Add {filename}", "--date", iso_date], env=env)
    return ds.repo.get_hexsha()


def _make_non_annex_source(tmp_path: Path) -> Dataset:
    """Fresh non-annex source dataset with one seed commit."""
    src = dl.create(path=tmp_path / "src", annex=False)
    _commit_at(src, "seed.txt", "2020-01-01T00:00:00+00:00")
    return src


def _head(ds: Dataset) -> str:
    return ds.repo.call_git(["symbolic-ref", "--short", "HEAD"]).strip()


def _origin_head(ds: Dataset) -> str:
    return ds.repo.call_git(["symbolic-ref", "refs/remotes/origin/HEAD"]).strip()


def _rename_head(src: Dataset, new_name: str) -> None:
    current = _head(src)
    if current != new_name:
        src.repo.call_git(["branch", "-m", current, new_name])


class TestPickPreferredBranch:
    def test_no_main_or_master(self, tmp_path):
        src = _make_non_annex_source(tmp_path)
        _rename_head(src, "develop")
        ds_clone = clone(source=src.path, path=tmp_path / "clone")
        assert pick_preferred_branch(ds_clone) is None

    def test_only_master(self, tmp_path):
        src = _make_non_annex_source(tmp_path)
        _rename_head(src, "master")
        ds_clone = clone(source=src.path, path=tmp_path / "clone")
        assert pick_preferred_branch(ds_clone) == "master"

    def test_only_main(self, tmp_path):
        src = _make_non_annex_source(tmp_path)
        _rename_head(src, "main")
        ds_clone = clone(source=src.path, path=tmp_path / "clone")
        assert pick_preferred_branch(ds_clone) == "main"

    def test_both_main_newer(self, tmp_path):
        src = _make_non_annex_source(tmp_path)
        _rename_head(src, "master")
        src.repo.call_git(["checkout", "-b", "main"])
        _commit_at(src, "later.txt", "2025-01-01T00:00:00+00:00")
        ds_clone = clone(source=src.path, path=tmp_path / "clone")
        assert pick_preferred_branch(ds_clone) == "main"

    def test_both_master_newer(self, tmp_path):
        # `main` pinned at seed, `master` advanced past it.
        src = _make_non_annex_source(tmp_path)
        _rename_head(src, "master")
        src.repo.call_git(["branch", "main"])
        _commit_at(src, "later.txt", "2025-01-01T00:00:00+00:00")
        ds_clone = clone(source=src.path, path=tmp_path / "clone")
        assert pick_preferred_branch(ds_clone) == "master"


class TestEnsurePreferredBranchCheckedOut:
    def test_git_annex_default_switches_to_main(self, tmp_path):
        # Mimic the OpenNeuro/nemar failure mode: origin serves `git-annex` as
        # default, but a real `main` also exists.
        src = dl.create(path=tmp_path / "src", annex=True)
        _commit_at(src, "seed.txt", "2020-01-01T00:00:00+00:00")
        _rename_head(src, "main")
        src.repo.call_git(["symbolic-ref", "HEAD", "refs/heads/git-annex"])

        ds_clone = clone(source=src.path, path=tmp_path / "clone")
        assert _head(ds_clone) == "git-annex"

        ensure_preferred_branch_checked_out(ds_clone)

        assert _head(ds_clone) == "main"
        assert _origin_head(ds_clone) == "refs/remotes/origin/main"

    def test_switch_from_master_to_main_when_main_is_newer(self, tmp_path):
        src = _make_non_annex_source(tmp_path)
        _rename_head(src, "master")
        src.repo.call_git(["checkout", "-b", "main"])
        _commit_at(src, "later.txt", "2025-01-01T00:00:00+00:00")
        # Keep master as the served default.
        src.repo.call_git(["symbolic-ref", "HEAD", "refs/heads/master"])

        ds_clone = clone(source=src.path, path=tmp_path / "clone")
        assert _head(ds_clone) == "master"

        ensure_preferred_branch_checked_out(ds_clone)

        assert _head(ds_clone) == "main"
        assert _origin_head(ds_clone) == "refs/remotes/origin/main"

    def test_no_op_when_already_on_preferred(self, tmp_path):
        src = _make_non_annex_source(tmp_path)
        _rename_head(src, "main")
        ds_clone = clone(source=src.path, path=tmp_path / "clone")
        head_sha_before = ds_clone.repo.get_hexsha()

        ensure_preferred_branch_checked_out(ds_clone)

        assert _head(ds_clone) == "main"
        assert ds_clone.repo.get_hexsha() == head_sha_before
        assert _origin_head(ds_clone) == "refs/remotes/origin/main"

    def test_no_op_when_no_candidate(self, tmp_path):
        src = _make_non_annex_source(tmp_path)
        _rename_head(src, "develop")
        ds_clone = clone(source=src.path, path=tmp_path / "clone")
        head_before = _head(ds_clone)
        origin_head_before = _origin_head(ds_clone)

        ensure_preferred_branch_checked_out(ds_clone)

        assert _head(ds_clone) == head_before
        assert _origin_head(ds_clone) == origin_head_before
