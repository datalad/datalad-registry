"""Change RepoUrl.branches to a dict

Revision ID: 7d283978c4a9
Revises: 029941610de0
Create Date: 2024-04-16 01:40:57.193989

"""

from collections.abc import Callable
from typing import Any, cast

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import column, table

# revision identifiers, used by Alembic.
revision = "7d283978c4a9"
down_revision = "029941610de0"
branch_labels = None
depends_on = None


def _lst_to_dict(branches: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {
        branch["name"]: {
            "hexsha": branch["hexsha"],
            "last_commit_dt": branch["last_commit_dt"],
        }
        for branch in branches
    }


def _dict_to_lst(branches: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    return [
        {"name": branch_name, **branch_data}
        for branch_name, branch_data in branches.items()
    ]


def _migrate_branches(branches_trans_func: Callable[..., Any]) -> None:
    bind = op.get_bind()

    # Define a table representation with only the columns we need (id and branches)
    repo_url = table("repo_url", column("id", sa.Integer), column("branches", JSONB))

    # Execute a SELECT to fetch all rows
    rows = bind.execute(sa.select(repo_url)).all()

    for row in rows:
        branches = row.branches

        # Check if the branches data is not null
        if branches is not None:
            # Transform the list of branches into a dictionary keyed by branch name
            new_branches = branches_trans_func(branches)

            # Execute an UPDATE for each row
            bind.execute(
                repo_url.update()
                .filter(repo_url.c.id == cast(int, row.id))
                .values(branches=new_branches)
            )


def upgrade():
    _migrate_branches(_lst_to_dict)


def downgrade():
    _migrate_branches(_dict_to_lst)
