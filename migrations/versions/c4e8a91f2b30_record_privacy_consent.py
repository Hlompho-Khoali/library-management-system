"""Record privacy notice acceptance on verification applications

Revision ID: c4e8a91f2b30
Revises: 9c1d2e3f4a5b
Create Date: 2026-09-27

"""
from alembic import op
import sqlalchemy as sa


revision = "c4e8a91f2b30"
down_revision = "9c1d2e3f4a5b"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("verifications", schema=None) as batch_op:
        batch_op.add_column(sa.Column("privacy_consent_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("privacy_notice_version", sa.String(length=20), nullable=True))


def downgrade():
    with op.batch_alter_table("verifications", schema=None) as batch_op:
        batch_op.drop_column("privacy_notice_version")
        batch_op.drop_column("privacy_consent_at")