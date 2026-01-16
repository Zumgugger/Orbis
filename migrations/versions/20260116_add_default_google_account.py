"""Add default_google_account column to users table

Revision ID: 20260116_add_default_google_account
Revises: 20260107_add_note_types
Create Date: 2026-01-16

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260116_add_default_google_account"
down_revision = "768fc3fc1f19"
branch_labels = None
depends_on = None


def upgrade():
    # Add default_google_account column to users table
    op.add_column(
        "users",
        sa.Column(
            "default_google_account",
            sa.String(255),
            nullable=True,
            comment="Default Google account email for phone login",
        ),
    )


def downgrade():
    # Remove default_google_account column
    op.drop_column("users", "default_google_account")
