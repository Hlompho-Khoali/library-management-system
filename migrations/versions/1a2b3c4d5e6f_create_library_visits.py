"""Create library visit records

Revision ID: 1a2b3c4d5e6f
Revises: 283bbeedbb9e
Create Date: 2026-09-14

"""
from alembic import op
import sqlalchemy as sa


revision = "1a2b3c4d5e6f"
down_revision = "283bbeedbb9e"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "library_visits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("entry_at", sa.DateTime(), nullable=False),
        sa.Column("exit_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_library_visits_member_id",
        "library_visits",
        ["member_id"],
    )


def downgrade():
    op.drop_index("ix_library_visits_member_id", table_name="library_visits")
    op.drop_table("library_visits")
