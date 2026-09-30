"""Add ID review status and rejection reason tracking

Revision ID: 9c1d2e3f4a5b
Revises: 2b3c4d5e6f7a
Create Date: 2026-09-22

"""
from alembic import op
import sqlalchemy as sa


revision = "9c1d2e3f4a5b"
down_revision = "2b3c4d5e6f7a"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("verifications", schema=None) as batch_op:
        batch_op.add_column(sa.Column("rejection_reasons", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("rejection_comment", sa.Text(), nullable=True))

    with op.batch_alter_table("members", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "id_review_status",
                sa.String(length=20),
                nullable=False,
                server_default="approved",
            )
        )
        batch_op.add_column(sa.Column("id_rejection_reasons", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("id_rejection_comment", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("verification_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "members_verification_id_fkey",
            "verifications",
            ["verification_id"],
            ["id"],
        )

    with op.batch_alter_table("members", schema=None) as batch_op:
        batch_op.alter_column("id_review_status", server_default=None)


def downgrade():
    with op.batch_alter_table("members", schema=None) as batch_op:
        batch_op.drop_constraint("members_verification_id_fkey", type_="foreignkey")
        batch_op.drop_column("verification_id")
        batch_op.drop_column("id_rejection_comment")
        batch_op.drop_column("id_rejection_reasons")
        batch_op.drop_column("id_review_status")

    with op.batch_alter_table("verifications", schema=None) as batch_op:
        batch_op.drop_column("rejection_comment")
        batch_op.drop_column("rejection_reasons")
