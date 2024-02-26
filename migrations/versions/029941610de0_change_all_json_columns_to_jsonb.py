"""Change all JSON columns to JSONB

Revision ID: 029941610de0
Revises: e35239d06d44
Create Date: 2024-02-23 06:24:15.776236

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "029941610de0"
down_revision = "e35239d06d44"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("url_metadata", schema=None) as batch_op:
        batch_op.alter_column(
            "extraction_parameter",
            existing_type=postgresql.JSON(astext_type=sa.Text()),
            type_=postgresql.JSONB(astext_type=sa.Text()),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "extracted_metadata",
            existing_type=postgresql.JSON(astext_type=sa.Text()),
            type_=postgresql.JSONB(astext_type=sa.Text()),
            existing_nullable=False,
        )


def downgrade():
    with op.batch_alter_table("url_metadata", schema=None) as batch_op:
        batch_op.alter_column(
            "extracted_metadata",
            existing_type=postgresql.JSONB(astext_type=sa.Text()),
            type_=postgresql.JSON(astext_type=sa.Text()),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "extraction_parameter",
            existing_type=postgresql.JSONB(astext_type=sa.Text()),
            type_=postgresql.JSON(astext_type=sa.Text()),
            existing_nullable=False,
        )
