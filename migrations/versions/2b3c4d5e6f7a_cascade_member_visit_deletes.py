"""Cascade member deletion to library visits

Revision ID: 2b3c4d5e6f7a
Revises: 1a2b3c4d5e6f
Create Date: 2026-09-15

"""
from alembic import op


revision = "2b3c4d5e6f7a"
down_revision = "1a2b3c4d5e6f"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint(
        "library_visits_member_id_fkey",
        "library_visits",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "library_visits_member_id_fkey",
        "library_visits",
        "members",
        ["member_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade():
    op.drop_constraint(
        "library_visits_member_id_fkey",
        "library_visits",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "library_visits_member_id_fkey",
        "library_visits",
        "members",
        ["member_id"],
        ["id"],
    )