import os
from pathlib import Path
from typing import Optional
from uuid import UUID

import datalad.api as dl
from datalad.api import Dataset
from datalad.support.exceptions import CommandError
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


def _commit_at(
    ds: Dataset,
    filename: str,
    iso_date: str,
    committer_date: Optional[str] = None,
) -> str:
    """Add and commit `filename` with a controlled author/committer date.

    Note: The dates are spelled in UTC on purpose, so that the selection keeps
          being exercised against the rendering that used to break it: recent
          versions of `git for-each-ref` render a UTC date in its `iso8601-strict`
          form with a `Z` suffix, which `datetime.fromisoformat()` cannot parse
          before Python 3.11.
    """
    (Path(ds.path) / filename).write_text(f"content of {filename}\n")
    env = {
        **os.environ,
        "GIT_AUTHOR_DATE": iso_date,
        "GIT_COMMITTER_DATE": iso_date if committer_date is None else committer_date,
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


def _make_git_annex_default_source(tmp_path: Path) -> Dataset:
    """Annex source dataset that serves `git-annex` as its default branch.

    This mimics the OpenNeuro/nemar failure mode: a real `main` exists alongside.
    """
    src = dl.create(path=tmp_path / "src", annex=True)
    _commit_at(src, "seed.txt", "2020-01-01T00:00:00+00:00")
    _rename_head(src, "main")
    src.repo.call_git(["symbolic-ref", "HEAD", "refs/heads/git-annex"])
    return src


def _make_source_with_newer_main(tmp_path: Path) -> Dataset:
    """Source dataset that serves `master` as its default while `main` is newer."""
    src = _make_non_annex_source(tmp_path)
    _rename_head(src, "master")
    src.repo.call_git(["checkout", "-b", "main"])
    _commit_at(src, "later.txt", "2025-01-01T00:00:00+00:00")
    src.repo.call_git(["symbolic-ref", "HEAD", "refs/heads/master"])
    return src


def _make_source_with_dev_default(tmp_path: Path) -> Dataset:
    """Source dataset whose default branch, `dev`, is newer than its stale `master`.

    `dev` stands for any default branch that the owner of the dataset has chosen.
    """
    src = _make_non_annex_source(tmp_path)
    _rename_head(src, "master")
    src.repo.call_git(["checkout", "-b", "dev"])
    _commit_at(src, "newer.txt", "2025-01-01T00:00:00+00:00")
    return src


class TestPickPreferredBranch:
    def test_default_branch_chosen_by_the_dataset_owner(self, tmp_path):
        # A default branch that is neither `git-annex` nor `main`/`master` is the
        # deliberate choice of the owner of the dataset. It is honored even when a
        # stale `master` is still lying around at the origin remote.
        src = _make_source_with_dev_default(tmp_path)
        ds_clone = clone(source=src.path, path=tmp_path / "clone")
        assert pick_preferred_branch(ds_clone, "dev") == "dev"

    def test_no_main_or_master(self, tmp_path):
        src = _make_non_annex_source(tmp_path)
        _rename_head(src, "develop")
        ds_clone = clone(source=src.path, path=tmp_path / "clone")
        assert pick_preferred_branch(ds_clone, "develop") == "develop"

    def test_no_default_branch_and_no_main_or_master(self, tmp_path):
        src = _make_non_annex_source(tmp_path)
        _rename_head(src, "develop")
        ds_clone = clone(source=src.path, path=tmp_path / "clone")
        assert pick_preferred_branch(ds_clone, None) is None

    def test_git_annex_default_branch(self, tmp_path):
        src = _make_non_annex_source(tmp_path)
        _rename_head(src, "main")
        ds_clone = clone(source=src.path, path=tmp_path / "clone")
        assert pick_preferred_branch(ds_clone, "git-annex") == "main"

    def test_git_annex_default_branch_without_main_or_master(self, tmp_path):
        src = _make_non_annex_source(tmp_path)
        _rename_head(src, "develop")
        ds_clone = clone(source=src.path, path=tmp_path / "clone")
        assert pick_preferred_branch(ds_clone, "git-annex") == "git-annex"

    def test_only_master(self, tmp_path):
        src = _make_non_annex_source(tmp_path)
        _rename_head(src, "master")
        ds_clone = clone(source=src.path, path=tmp_path / "clone")
        assert pick_preferred_branch(ds_clone, "master") == "master"

    def test_only_main(self, tmp_path):
        src = _make_non_annex_source(tmp_path)
        _rename_head(src, "main")
        ds_clone = clone(source=src.path, path=tmp_path / "clone")
        assert pick_preferred_branch(ds_clone, "main") == "main"

    def test_both_main_newer(self, tmp_path):
        src = _make_source_with_newer_main(tmp_path)
        ds_clone = clone(source=src.path, path=tmp_path / "clone")
        assert pick_preferred_branch(ds_clone, "master") == "main"

    def test_both_master_newer(self, tmp_path):
        # `main` pinned at seed, `master` advanced past it.
        src = _make_non_annex_source(tmp_path)
        _rename_head(src, "master")
        src.repo.call_git(["branch", "main"])
        _commit_at(src, "later.txt", "2025-01-01T00:00:00+00:00")
        ds_clone = clone(source=src.path, path=tmp_path / "clone")
        assert pick_preferred_branch(ds_clone, "main") == "master"

    def test_tie_between_main_and_master_goes_to_main(self, tmp_path):
        # A repo that has just renamed `master` to `main` and kept both names
        # pointing at the same commit
        src = _make_non_annex_source(tmp_path)
        _rename_head(src, "master")
        src.repo.call_git(["branch", "main"])
        ds_clone = clone(source=src.path, path=tmp_path / "clone")
        assert pick_preferred_branch(ds_clone, "master") == "main"

    def test_ranking_by_committer_date(self, tmp_path):
        # `main` carries a tip applied recently from an old patch, so its author
        # date predates that of the tip of the long abandoned `master`. `main` is
        # nonetheless the branch that has moved most recently.
        src = _make_non_annex_source(tmp_path)
        _rename_head(src, "master")
        _commit_at(src, "abandoned.txt", "2019-01-01T00:00:00+00:00")
        src.repo.call_git(["checkout", "-b", "main"])
        _commit_at(
            src,
            "applied_patch.txt",
            "2018-01-01T00:00:00+00:00",
            committer_date="2025-01-01T00:00:00+00:00",
        )
        ds_clone = clone(source=src.path, path=tmp_path / "clone")
        assert pick_preferred_branch(ds_clone, "master") == "main"


class TestEnsurePreferredBranchCheckedOut:
    def test_git_annex_default_switches_to_main(self, tmp_path):
        src = _make_git_annex_default_source(tmp_path)

        ds_clone = clone(source=src.path, path=tmp_path / "clone")
        assert _head(ds_clone) == "git-annex"

        ensure_preferred_branch_checked_out(ds_clone)

        assert _head(ds_clone) == "main"
        assert _origin_head(ds_clone) == "refs/remotes/origin/main"

    def test_switch_from_master_to_main_when_main_is_newer(self, tmp_path):
        src = _make_source_with_newer_main(tmp_path)

        ds_clone = clone(source=src.path, path=tmp_path / "clone")
        assert _head(ds_clone) == "master"

        ensure_preferred_branch_checked_out(ds_clone)

        assert _head(ds_clone) == "main"
        assert _origin_head(ds_clone) == "refs/remotes/origin/main"

    def test_upstream_branch_of_the_branch_switched_to(self, tmp_path):
        # `update_ds_clone()` decides between a fast-forward and a reclone by
        # comparing `get_origin_upstream_branch()` with `pick_preferred_branch()`,
        # so the branch switched to must have its upstream branch set
        src = _make_source_with_newer_main(tmp_path)

        ds_clone = clone(source=src.path, path=tmp_path / "clone")

        ensure_preferred_branch_checked_out(ds_clone)

        assert get_origin_upstream_branch(ds_clone) == "main"

    def test_ds_id_after_switching_away_from_git_annex(self, tmp_path):
        # The `.datalad/config` that carries the dataset ID is only materialized in
        # the working tree by the switch, so the config of the clone must be reloaded
        # for `Dataset.id` to report it.
        src = _make_git_annex_default_source(tmp_path)

        ds_clone = clone(source=src.path, path=tmp_path / "clone")
        assert _head(ds_clone) == "git-annex"
        assert ds_clone.id is None

        ensure_preferred_branch_checked_out(ds_clone)

        assert _head(ds_clone) == "main"
        assert ds_clone.id == src.id

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

    def test_no_op_on_default_branch_chosen_by_the_dataset_owner(self, tmp_path):
        # The stale `master` at the origin remote must not displace `dev`
        src = _make_source_with_dev_default(tmp_path)
        ds_clone = clone(source=src.path, path=tmp_path / "clone")
        assert _head(ds_clone) == "dev"
        origin_head_before = _origin_head(ds_clone)

        ensure_preferred_branch_checked_out(ds_clone)

        assert _head(ds_clone) == "dev"
        assert _origin_head(ds_clone) == origin_head_before
        assert (Path(ds_clone.path) / "newer.txt").exists()

    def test_detached_head(self, tmp_path):
        # A detached HEAD must not raise. `git clone` does not leave one behind,
        # but an exception here is expensive: in `chk_url_to_update()` it counts
        # toward `DATALAD_REGISTRY_MAX_FAILED_CHKS_PER_URL`.
        src = _make_non_annex_source(tmp_path)
        _rename_head(src, "main")
        ds_clone = clone(source=src.path, path=tmp_path / "clone")
        ds_clone.repo.call_git(["checkout", "--detach"])

        ensure_preferred_branch_checked_out(ds_clone)

        assert _head(ds_clone) == "main"

    def test_detached_head_with_default_branch_chosen_by_the_dataset_owner(
        self, tmp_path
    ):
        # A detached HEAD must not cost the protection of the chosen default
        # branch: `refs/remotes/origin/HEAD`, not the branch checked out, is what
        # says which branch the origin remote advertises
        src = _make_source_with_dev_default(tmp_path)
        ds_clone = clone(source=src.path, path=tmp_path / "clone")
        ds_clone.repo.call_git(["checkout", "--detach"])

        ensure_preferred_branch_checked_out(ds_clone)

        assert _head(ds_clone) == "dev"
        assert _origin_head(ds_clone) == "refs/remotes/origin/dev"

    def test_origin_head_of_a_clone_without_one(self, tmp_path):
        # An origin remote advertising no default branch leaves the clone without
        # `refs/remotes/origin/HEAD`, which `_update_dataset_url_info()` reads
        src = _make_non_annex_source(tmp_path)
        _rename_head(src, "main")
        ds_clone = clone(source=src.path, path=tmp_path / "clone")
        # `--delete`, for `git update-ref -d` would follow the symbolic ref and
        # delete `refs/remotes/origin/main` instead
        ds_clone.repo.call_git(["symbolic-ref", "--delete", "refs/remotes/origin/HEAD"])

        ensure_preferred_branch_checked_out(ds_clone)

        assert _head(ds_clone) == "main"
        assert _origin_head(ds_clone) == "refs/remotes/origin/main"

    def test_no_op_without_origin_head_and_without_candidate(self, tmp_path):
        # Nothing to go on: no `refs/remotes/origin/HEAD`, no branch checked out,
        # and no `main`/`master` at the origin remote
        src = _make_non_annex_source(tmp_path)
        _rename_head(src, "develop")
        ds_clone = clone(source=src.path, path=tmp_path / "clone")
        ds_clone.repo.call_git(["symbolic-ref", "--delete", "refs/remotes/origin/HEAD"])
        ds_clone.repo.call_git(["checkout", "--detach"])

        ensure_preferred_branch_checked_out(ds_clone)

        assert ds_clone.repo.get_active_branch() is None
        with pytest.raises(CommandError):
            _origin_head(ds_clone)
