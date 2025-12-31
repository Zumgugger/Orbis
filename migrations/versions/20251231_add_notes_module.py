"""Add notes and note_categories tables

Revision ID: 20251231_add_notes_module
Revises:
Create Date: 2025-12-31
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20251231_add_notes_module"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create note_categories table
    op.create_table(
        "note_categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_note_categories_user", "note_categories", ["user_id"])

    # Create notes table
    op.create_table(
        "notes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("note_type", sa.String(50), nullable=False, server_default="journal"),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("entry_date", sa.Date(), nullable=True),
        sa.Column("pinned", sa.Boolean(), nullable=True, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["category_id"], ["note_categories.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notes_user_updated", "notes", ["user_id", "updated_at"])
    op.create_index("ix_notes_user_type", "notes", ["user_id", "note_type"])
    op.create_index("ix_notes_user_date", "notes", ["user_id", "entry_date"])


def downgrade():
    op.drop_index("ix_notes_user_date", table_name="notes")
    op.drop_index("ix_notes_user_type", table_name="notes")
    op.drop_index("ix_notes_user_updated", table_name="notes")
    op.drop_table("notes")
    op.drop_index("ix_note_categories_user", table_name="note_categories")
    op.drop_table("note_categories")
