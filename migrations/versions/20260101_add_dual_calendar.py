"""Add dual calendar support (shared calendar fields)

Revision ID: 20260101_add_dual_calendar
Revises: 69786f18613d_add_google_event_id_to_todos
Create Date: 2026-01-01

Adds:
- User.shared_calendar_id: Secondary calendar ID for family blocks
- Todo.sync_to_shared: Boolean flag to sync to shared calendar
- Todo.shared_title: Block title for shared calendar (Work, Konzert, etc.)
- Todo.shared_event_id: Google event ID in shared calendar
- SharedTitle table: Frequently used shared calendar titles
"""
from datetime import datetime

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260101_add_dual_calendar"
down_revision = "69786f18613d"
branch_labels = None
depends_on = None

# Default shared titles to seed
DEFAULT_TITLES = [
    {"title": "Work", "is_default_work_hours": True, "position": 0},
    {"title": "Sitzung", "is_default_work_hours": False, "position": 1},
    {"title": "Musik", "is_default_work_hours": False, "position": 2},
    {"title": "Konzert", "is_default_work_hours": False, "position": 3},
]


def upgrade():
    # Add shared_calendar_id to users table
    op.add_column(
        "users", sa.Column("shared_calendar_id", sa.String(255), nullable=True)
    )

    # Add shared calendar fields to todos table
    op.add_column(
        "todos",
        sa.Column("sync_to_shared", sa.Boolean(), nullable=True, server_default="0"),
    )
    op.add_column("todos", sa.Column("shared_title", sa.String(50), nullable=True))
    op.add_column("todos", sa.Column("shared_event_id", sa.String(255), nullable=True))

    # Create shared_titles table
    op.create_table(
        "shared_titles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(50), nullable=False),
        sa.Column(
            "is_default_work_hours", sa.Boolean(), nullable=True, server_default="0"
        ),
        sa.Column("position", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "title", name="uq_shared_titles_user_title"),
    )
    op.create_index("ix_shared_titles_user", "shared_titles", ["user_id"], unique=False)

    # Seed default shared titles for existing users
    conn = op.get_bind()
    users = conn.execute(sa.text("SELECT id FROM users")).fetchall()
    for (user_id,) in users:
        for title_data in DEFAULT_TITLES:
            conn.execute(
                sa.text(
                    "INSERT INTO shared_titles (user_id, title, is_default_work_hours, position, created_at) "
                    "VALUES (:user_id, :title, :is_default, :position, :created_at)"
                ),
                {
                    "user_id": user_id,
                    "title": title_data["title"],
                    "is_default": title_data["is_default_work_hours"],
                    "position": title_data["position"],
                    "created_at": datetime.utcnow(),
                },
            )


def downgrade():
    # Drop shared_titles table
    op.drop_index("ix_shared_titles_user", table_name="shared_titles")
    op.drop_table("shared_titles")

    # Remove shared calendar fields from todos
    op.drop_column("todos", "shared_event_id")
    op.drop_column("todos", "shared_title")
    op.drop_column("todos", "sync_to_shared")

    # Remove shared_calendar_id from users
    op.drop_column("users", "shared_calendar_id")
