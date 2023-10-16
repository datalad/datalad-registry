"""Changing the branches column to JSONB type

Revision ID: e35239d06d44
Revises: a398e7225012
Create Date: 2023-08-11 01:49:16.820526

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "e35239d06d44"
down_revision = "a398e7225012"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("repo_url", schema=None) as batch_op:
        batch_op.alter_column(
            "branches",
            existing_type=sa.Text(),
            type_=postgresql.JSONB(),
            existing_nullable=True,
            postgresql_using="branches::jsonb",
        )


def downgrade():
    with op.batch_alter_table("repo_url", schema=None) as batch_op:
        batch_op.alter_column(
            "branches",
            existing_type=postgresql.JSONB(),
            type_=sa.Text(),
            existing_nullable=True,
            postgresql_using="branches::text",
        )
