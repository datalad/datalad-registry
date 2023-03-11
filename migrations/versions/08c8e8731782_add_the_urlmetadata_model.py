"""Add the URLMetadata model

Revision ID: 08c8e8731782
Revises: 769fc6a4d2ea
Create Date: 2023-03-11 13:00:08.934405

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "08c8e8731782"
down_revision = "769fc6a4d2ea"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "url_metadata",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dataset_describe", sa.String(length=60), nullable=False),
        sa.Column("dataset_version", sa.String(length=60), nullable=False),
        sa.Column("extractor_name", sa.String(length=100), nullable=False),
        sa.Column("extractor_version", sa.String(length=60), nullable=False),
        sa.Column("extraction_parameter", sa.JSON(), nullable=False),
        sa.Column("extracted_metadata", sa.JSON(), nullable=False),
        sa.Column("url_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["url_id"],
            ["url.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("url_metadata")
    # ### end Alembic commands ###
