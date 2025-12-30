"""add_todo_time_scheduling_fields

Revision ID: 20251231_add_todo_time_fields
Revises: 20251227_drop_idea_file_legacy_columns
Create Date: 2025-12-31

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20251231_add_todo_time_fields"
down_revision = "20251227_drop_idea_file_legacy_columns"
branch_labels = None
depends_on = None


def upgrade():
    # Add time scheduling fields to todos table
    op.add_column("todos", sa.Column("due_time", sa.Time(), nullable=True))
    op.add_column("todos", sa.Column("end_time", sa.Time(), nullable=True))
    op.add_column("todos", sa.Column("duration_minutes", sa.Integer(), nullable=True))
    op.create_index(
        "ix_todos_user_due_time",
        "todos",
        ["user_id", "due_date", "due_time"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_todos_user_due_time", table_name="todos")
    op.drop_column("todos", "duration_minutes")
    op.drop_column("todos", "end_time")
    op.drop_column("todos", "due_time")
