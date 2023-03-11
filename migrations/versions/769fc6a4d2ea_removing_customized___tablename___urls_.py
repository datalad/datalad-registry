"""Removing customized __tablename__ urls, and let URL model to assume default name

Revision ID: 769fc6a4d2ea
Revises:
Create Date: 2023-03-10 17:30:48.983791

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "769fc6a4d2ea"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.rename_table("urls", "url")


def downgrade():
    op.rename_table("url", "urls")
