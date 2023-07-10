"""Prepare  model for update function

Revision ID: c6873af75bd6
Revises: 7a22e9d79946
Create Date: 2023-07-07 18:30:17.831328

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "c6873af75bd6"
down_revision = "7a22e9d79946"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("url", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("head_dt", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("last_chk_dt", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("chk_req_dt", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "n_failed_chks", sa.Integer(), server_default=text("0"), nullable=False
            )
        )
        batch_op.drop_column("update_announced")


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("url", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "update_announced", sa.BOOLEAN(), autoincrement=False, nullable=False
            )
        )
        batch_op.drop_column("n_failed_chks")
        batch_op.drop_column("chk_req_dt")
        batch_op.drop_column("last_chk_dt")
        batch_op.drop_column("head_dt")

    # ### end Alembic commands ###
