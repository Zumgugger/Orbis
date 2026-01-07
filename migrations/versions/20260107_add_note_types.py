"""Add note_types table and note_type_id column

Revision ID: 20260107_add_note_types
Revises: d2282fc449a4
Create Date: 2026-01-07
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260107_add_note_types"
down_revision = "d2282fc449a4"
branch_labels = None
depends_on = None


def upgrade():
    # Create note_types table
    op.create_table(
        "note_types",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column(
            "icon", sa.String(length=50), nullable=True, server_default="bi-file-text"
        ),
        sa.Column("position", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_note_type_user_name"),
    )
    op.create_index("ix_note_types_user", "note_types", ["user_id"])

    # Add note_type_id column to notes table
    op.add_column("notes", sa.Column("note_type_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_notes_note_type_id", "notes", "note_types", ["note_type_id"], ["id"]
    )
    op.create_index("ix_notes_user_type_id", "notes", ["user_id", "note_type_id"])


def downgrade():
    op.drop_index("ix_notes_user_type_id", table_name="notes")
    op.drop_constraint("fk_notes_note_type_id", "notes", type_="foreignkey")
    op.drop_column("notes", "note_type_id")
    op.drop_index("ix_note_types_user", table_name="note_types")
    op.drop_table("note_types")
