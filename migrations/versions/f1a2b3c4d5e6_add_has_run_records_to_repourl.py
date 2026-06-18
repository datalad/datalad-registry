"""Add has_run_records to RepoUrl

Revision ID: f1a2b3c4d5e6
Revises: e35239d06d44
Create Date: 2026-02-06 16:38:15.749000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "f1a2b3c4d5e6"
down_revision = "e35239d06d44"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("repo_url", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("has_run_records", sa.Boolean(), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("repo_url", schema=None) as batch_op:
        batch_op.drop_column("has_run_records")
