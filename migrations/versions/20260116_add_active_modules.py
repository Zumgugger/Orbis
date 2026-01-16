"""Add active_modules column to users table

Revision ID: 20260116_add_active_modules
Revises: 20260116_add_default_google_account
Create Date: 2026-01-16

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260116_add_active_modules"
down_revision = "20260116_add_default_google_account"
branch_labels = None
depends_on = None


def upgrade():
    # Add active_modules column to users table
    op.add_column(
        "users",
        sa.Column(
            "active_modules",
            sa.Text,
            nullable=True,
            comment="JSON string of active module names",
        ),
    )


def downgrade():
    # Remove active_modules column
    op.drop_column("users", "active_modules")
