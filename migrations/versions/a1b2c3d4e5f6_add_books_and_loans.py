"""Add books and loans

Revision ID: a1b2c3d4e5f6
Revises: f7a8b9c0d1e2
Create Date: 2026-10-06

"""
from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("members", sa.Column("block_reason", sa.String(30), nullable=True))

    op.create_table(
        "books",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("author", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_books_item_id", "books", ["item_id"], unique=True)

    op.create_table(
        "loans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("checked_out_at", sa.DateTime(), nullable=False),
        sa.Column("due_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column("fee_paid", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"]),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_loans_book_id", "loans", ["book_id"])
    op.create_index("ix_loans_member_id", "loans", ["member_id"])


def downgrade():
    op.drop_index("ix_loans_member_id", table_name="loans")
    op.drop_index("ix_loans_book_id", table_name="loans")
    op.drop_table("loans")
    op.drop_index("ix_books_item_id", table_name="books")
    op.drop_table("books")
    op.drop_column("members", "block_reason")
