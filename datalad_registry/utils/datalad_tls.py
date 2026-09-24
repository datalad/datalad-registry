from dataclasses import dataclass
import re
from typing import Optional
from uuid import UUID

from datalad import api as dl
from datalad.api import Dataset
from datalad.support.exceptions import CommandError

# The branches, in order of preference for breaking a tie, that are considered
# for tracking when the default branch advertised by the origin remote is not a
# branch of the dataset content.
# See https://github.com/datalad/datalad-registry/issues/414
_PREFERRED_BRANCH_CANDIDATES = ("main", "master")

_ANNEX_BRANCH = "git-annex"


@dataclass
class WtAnnexedFileInfo:
    """
    Represent information about annexed files in the working tree of a datalad dataset
    that is a git-annex repo
    """

    count: int
    size: int


def clone(*args, **kwargs) -> dl.Dataset:
    """
    Clone (copy) a dataset from a given URL or local directory

    All parameters of this function are the same as `datalad.api.clone` with the
    exception that the keyword parameter `return_type` is not supported.

    :raises TypeError: Calling this function with the keyword argument of `return_type`
    :raises RuntimeError: If the cloning process fails to produce
                          a `datalad.api.Dataset` object even after successfully
                          copying the dataset from the given URL or local directory
    :return: A `datalad.api.Dataset` object representing the clone/copy of the dataset
    """
    if "return_type" in kwargs:
        raise TypeError("'return_type' is not a supported keyword argument")

    ds = dl.clone(*args, return_type="item-or-list", **kwargs)

    # Ensure that a Dataset object is produced upon a successful cloning
    if not isinstance(ds, dl.Dataset):
        raise RuntimeError("Cloning of a dataset failed to produce a Dataset object")

    return ds


def get_origin_annex_uuid(ds: Dataset) -> Optional[UUID]:
    """
    Get the annex UUID of the origin remote of a given dataset

    :param ds: The dataset
    :return: The annex UUID of the origin remote of the given dataset if it exists;
             None otherwise.
    """

    return (
        UUID(uuid_str)
        if (uuid_str := ds.config.get("remote.origin.annex-uuid")) is not None
        else None
    )


def get_origin_annex_key_count(ds: Dataset) -> Optional[int]:
    """
    Get "remote annex keys" of the origin remote of a given dataset

    :param ds: The given dataset
    :return: In the case that the dataset is a git-annex repo, the "remote annex keys"
             of the origin remote of the given dataset is returned.
             In the case that the dataset is not a git-annex repo, return None.
    """
    if ds.repo.is_with_annex():
        return ds.repo.call_annex_records(["info"], "origin")[0]["remote annex keys"]
    else:
        return None


def get_wt_annexed_file_info(ds: Dataset) -> Optional[WtAnnexedFileInfo]:
    """
    Get information about annexed files in the working tree of a given datalad dataset

    :param ds: The given dataset
    :return: In the case that the dataset is a git-annex repo, information about
             annexed files in the working tree of the dataset is returned.
             In the case that the dataset is not a git-annex repo, return None.
    """
    if ds.repo.is_with_annex():
        annex_record = ds.repo.call_annex_records(["info", "--bytes"], ".")[0]

        return WtAnnexedFileInfo(
            count=annex_record["annexed files in working tree"],
            size=int(annex_record["size of annexed files in working tree"]),
        )
    else:
        return None


def get_head_describe(ds: Dataset) -> str:
    """
    Get the output of `git describe --tags --always` of a given dataset

    :param ds: The given dataset
    :return: The output of `git describe --tags --always` of the given dataset
    """
    return ds.repo.describe(tags=True, always=True)


def _get_origin_branch_info(
    ds: Dataset, fields: list[str]
) -> dict[str, dict[str, str]]:
    """
    Get the given `git for-each-ref` fields of the branches of the origin remote
    of a given dataset

    :param ds: The given dataset
    :param fields: The `git for-each-ref` fields to report for each branch
    :return: A dictionary in which the keys are the branch names and the values are
             dictionaries keyed by the field specifications, those of the requested
             fields and `refname:strip=3`, which is always reported

    Note: The information is obtained from the remote-tracking refs,
          `refs/remotes/origin/*`, of the given dataset. It is therefore only as
          up-to-date as the last (pruning) fetch from the origin remote.
    """
    return {
        branch_name: branch_info
        for branch_info in ds.repo.for_each_ref_(
            pattern="refs/remotes/origin/",
            fields=["refname:strip=3", *fields],
        )
        if (branch_name := branch_info["refname:strip=3"]) != "HEAD"
    }


def get_origin_branches(ds: Dataset) -> dict[str, dict[str, str]]:
    """
    Get the branches of the origin remote of a given dataset

    :param ds: The given dataset
    :return: A dictionary representing the branches of the origin remote
             of the given dataset. Each branch is represented by a key-value pair in
             which the key is the branch name and the value is a dictionary with keys,
             "hexsha" and "last_commit_dt".
             The value of "hexsha" is the hash of the last commit in the branch,
             and the value of "last_commit_dt" is the datetime of the last commit
             in the branch.

    Note: "last_commit_dt" carries the *author* date, as it always has, so that the
          values reported by the API stay spelled as the ones already stored.
          `pick_preferred_branch()` deliberately reads the *committer* date instead,
          that being the one that says which branch has moved most recently.
    """
    return {
        branch_name: {
            "hexsha": branch_info["objectname"],
            "last_commit_dt": branch_info["authordate:iso8601-strict"],
        }
        for branch_name, branch_info in _get_origin_branch_info(
            ds, ["objectname", "authordate:iso8601-strict"]
        ).items()
    }


def get_origin_default_branch(ds: Dataset) -> str:
    """
    Get the name of the default branch of the origin remote of a given dataset

    :param ds: The given dataset
    :return: The name of the default branch of the origin remote of the given dataset

    Note: The given dataset must be a git repo with a remote named "origin"
    """
    ls_remote_output = ds.repo.call_git(["ls-remote", "--symref", "origin", "HEAD"])

    match = re.search(r"ref: refs/heads/(\S+)\s+HEAD", ls_remote_output)

    if match is None:
        raise RuntimeError(
            "Failed to extract the name of the default branch of the original remote "
            "from the output of `git ls-remote --symref origin HEAD`"
        )

    return match.group(1)


def pick_preferred_branch(ds: Dataset, default_branch: Optional[str]) -> Optional[str]:
    """
    Pick the branch of the origin remote of a given dataset that is to be tracked

    :param ds: The given dataset
    :param default_branch: The name of the branch that the origin remote advertises
                           as its default, or `None` if there is no such branch to
                           honor
    :return: `default_branch` as given, except when it is the `git-annex` branch or
             one of `main`/`master`. In those cases, the name of the
             more-recently-committed-to of the `main`/`master` branches present at
             the origin remote is returned, with `default_branch` returned as a
             fallback when neither of them is present. `None` is returned only when
             `default_branch` is `None` and neither `main` nor `master` is present.

    Note: A default branch of the origin remote that is neither `git-annex` nor one
          of `main`/`master`, e.g. `dev`, is a deliberate choice of the owner of the
          dataset and is therefore always honored.
          See https://github.com/datalad/datalad-registry/issues/414
    Note: The choice between `main` and `master` is symmetric, by recency alone, as
          the issue above asks. An advertised `master` therefore loses to a more
          recently committed-to `main`, and an advertised `main` to a more recently
          committed-to `master`.
    Note: Known limitation: when the origin remote advertises `git-annex` and has
          neither `main` nor `master`, `git-annex` is returned, there being no
          candidate to prefer over it, and the dataset goes on being tracked by its
          `git-annex` branch.
    Note: This function reads the remote-tracking refs of the given dataset. They
          must be up-to-date, by a fresh clone or a `git fetch --prune`, for the
          selection to reflect the current state of the origin remote.
    """
    if default_branch is not None and default_branch not in (
        _ANNEX_BRANCH,
        *_PREFERRED_BRANCH_CANDIDATES,
    ):
        return default_branch

    # `committerdate`, not `authordate`, for it is the field that answers which
    # branch has moved most recently. `authordate` is preserved by rebases,
    # `git am`, cherry-picks, and history imports.
    branch_info = _get_origin_branch_info(ds, ["committerdate:unix"])

    # Note: The insertion order is that of `_PREFERRED_BRANCH_CANDIDATES`
    candidates = {
        name: int(branch_info[name]["committerdate:unix"])
        for name in _PREFERRED_BRANCH_CANDIDATES
        # A ref that is not a commit, of which there should be none among these,
        # renders an empty committer date
        if branch_info.get(name, {}).get("committerdate:unix")
    }

    if not candidates:
        return default_branch

    # `max()` returns the first of the equally ranked elements. `main` therefore wins
    # a tie with `master`, as in a repo that has just renamed `master` to `main` and
    # kept both names pointing at the same commit.
    return max(candidates, key=lambda name: candidates[name])


def _get_local_origin_default_branch(ds: Dataset) -> Optional[str]:
    """
    Get the name of the default branch of the origin remote of a given dataset as
    recorded locally, in `refs/remotes/origin/HEAD`

    :param ds: The given dataset
    :return: The name of the branch that the local `refs/remotes/origin/HEAD` points
             at, or `None` when the given dataset has no such ref, as is the case
             for a clone of an origin remote that advertises no default branch

    Note: Unlike `get_origin_default_branch()`, this function reads a local ref only
          and so costs no round trip to the origin remote. `git clone` writes that
          ref, `git fetch` does not update it, so it reports the origin remote as of
          the last clone.
    """
    try:
        ref = ds.repo.call_git(
            ["symbolic-ref", "refs/remotes/origin/HEAD"], expect_fail=True
        ).strip()
    except CommandError:
        return None

    prefix = "refs/remotes/origin/"
    return ref[len(prefix) :] if ref.startswith(prefix) else None


def ensure_preferred_branch_checked_out(ds: Dataset) -> None:
    """
    Ensure that the branch to be tracked of a given clone of a dataset is the branch
    checked out in it

    Check out `pick_preferred_branch()` of the given clone and point the local
    `refs/remotes/origin/HEAD` at it, so that downstream readers of `origin/HEAD`,
    such as `_update_dataset_url_info()`, see the corrected default. Either step is
    skipped when it has nothing to correct.

    :param ds: The given clone of a dataset. The branch that the origin remote
               advertises as its default is read from the local
               `refs/remotes/origin/HEAD` of the clone, and taken from the branch
               checked out in it only when that ref is absent.

    Note: The remote-tracking refs of the given clone must be up-to-date, by a fresh
          clone or a `git fetch --prune`, for the selection to reflect the current
          state of the origin remote.
    """
    origin_default_branch = _get_local_origin_default_branch(ds)

    # `None` in the case of a detached HEAD
    current_branch = ds.repo.get_active_branch()

    preferred_branch = pick_preferred_branch(
        ds,
        current_branch if origin_default_branch is None else origin_default_branch,
    )

    if preferred_branch is None:
        return

    if preferred_branch != current_branch:
        # -f: clones landing on `git-annex` leave `uuid.log` dirty in the
        # working tree, which blocks a plain checkout.
        ds.repo.call_git(
            ["checkout", "-f", "-B", preferred_branch, f"origin/{preferred_branch}"]
        )

        # The checkout above has just put a different working tree, and with it
        # possibly a `.datalad/config` that was absent before, on disk. Without this
        # reload, the config manager keeps answering from its clone-time snapshot,
        # and `ds.id` of a dataset cloned with the `git-annex` branch checked out
        # stays `None`.
        ds.config.reload()

    if origin_default_branch != preferred_branch:
        # This also creates the ref for a clone of an origin remote that advertises
        # no default branch
        ds.repo.call_git(
            [
                "symbolic-ref",
                "refs/remotes/origin/HEAD",
                f"refs/remotes/origin/{preferred_branch}",
            ]
        )


def get_origin_upstream_branch(ds: Dataset) -> Optional[str]:
    """
    Get the name of the upstream branch at the origin remote of the current local branch
    of a given dataset

    :param ds: The given dataset
    :return: The name of the upstream branch at the origin remote of the current local
             branch of the given dataset, or `None` if `git rev-parse` fails to
             resolve one, as it does, for example, for a local branch with no
             upstream branch configured and for one whose remote-tracking ref is gone

    Note: The given dataset must be a git repo with a remote named "origin"
    """
    try:
        rev_parse_output = ds.repo.call_git(
            ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
            expect_fail=True,
        )
    except CommandError:
        return None

    match = re.search(r"origin/(\S+)", rev_parse_output)

    if match is None:
        raise RuntimeError(
            "Failed to extract the name of the upstream branch at the origin remote "
            "of the current local branch from the output of "
            "`git rev-parse --abbrev-ref --symbolic-full-name @{u}`"
        )

    return match.group(1)
