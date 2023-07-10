"""Rename model URL to RepoUrl

Revision ID: a398e7225012
Revises: c6873af75bd6
Create Date: 2023-07-08 21:43:12.767961

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "a398e7225012"
down_revision = "c6873af75bd6"
branch_labels = None
depends_on = None


def upgrade():

    op.rename_table("url", "repo_url")

    with op.batch_alter_table("url_metadata", schema=None) as batch_op:
        batch_op.drop_constraint("url_metadata_url_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(None, "repo_url", ["url_id"], ["id"])


def downgrade():

    with op.batch_alter_table("url_metadata", schema=None) as batch_op:
        batch_op.drop_constraint(None, type_="foreignkey")
        batch_op.create_foreign_key(
            "url_metadata_url_id_fkey", "url", ["url_id"], ["id"]
        )

    op.rename_table("repo_url", "url")
