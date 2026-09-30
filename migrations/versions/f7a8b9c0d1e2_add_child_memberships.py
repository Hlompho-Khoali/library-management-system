"""Add parent links for child memberships

Revision ID: f7a8b9c0d1e2
Revises: d5a82fce08bf
Create Date: 2026-09-29 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "f7a8b9c0d1e2"
down_revision = "c4e8a91f2b30"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("members", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("parent_id", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "is_child",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.create_index(
            "ix_members_parent_id",
            ["parent_id"],
            unique=False,
        )
        batch_op.create_foreign_key(
            "fk_members_parent_id_members",
            "members",
            ["parent_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.alter_column("is_child", server_default=None)


def downgrade():
    with op.batch_alter_table("members", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_members_parent_id_members",
            type_="foreignkey",
        )
        batch_op.drop_index("ix_members_parent_id")
        batch_op.drop_column("is_child")
        batch_op.drop_column("parent_id")