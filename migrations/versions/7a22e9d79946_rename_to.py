"""Rename  `info_ts` to `last_update_dt`

Revision ID: 7a22e9d79946
Revises: a26ee17e3a75
Create Date: 2023-07-07 13:54:39.373339

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "7a22e9d79946"
down_revision = "a26ee17e3a75"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        table_name="url", column_name="info_ts", new_column_name="last_update_dt"
    )


def downgrade():
    op.alter_column(
        table_name="url", column_name="last_update_dt", new_column_name="info_ts"
    )
