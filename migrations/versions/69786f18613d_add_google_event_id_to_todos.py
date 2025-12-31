"""add_google_event_id_to_todos

Revision ID: 69786f18613d
Revises: 20251231_add_todo_time_fields
Create Date: 2025-12-31 00:57:24.352189

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "69786f18613d"
down_revision = "20251231_add_todo_time_fields"
branch_labels = None
depends_on = None


def upgrade():
    # Add google_event_id column to todos table
    op.add_column(
        "todos",
        sa.Column("google_event_id", sa.String(length=255), nullable=True),
    )


def downgrade():
    # Remove google_event_id column from todos table
    op.drop_column("todos", "google_event_id")
