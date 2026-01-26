"""Add daily stats table and idea checklist

Revision ID: 20260126_add_stats_checklist
Revises: 20260116_add_active_modules
Create Date: 2026-01-26

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260126_add_stats_checklist"
down_revision = "20260116_add_active_modules"
branch_labels = None
depends_on = None


def upgrade():
    # Create daily_stats table
    op.create_table(
        "daily_stats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("stat_date", sa.Date(), nullable=False),
        sa.Column("todos_completed", sa.Integer(), default=0),
        sa.Column("todos_total", sa.Integer(), default=0),
        sa.Column("dailies_completed", sa.Integer(), default=0),
        sa.Column("dailies_total", sa.Integer(), default=0),
        sa.Column("habits_completed", sa.Integer(), default=0),
        sa.Column("habits_total", sa.Integer(), default=0),
        sa.Column("total_completed", sa.Integer(), default=0),
        sa.Column("total_items", sa.Integer(), default=0),
        sa.Column("completion_percentage", sa.Integer(), default=0),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "stat_date", name="uq_daily_stats_user_date"),
    )
    op.create_index("ix_daily_stats_user_date", "daily_stats", ["user_id", "stat_date"])

    # Add checklist_data column to ideas table
    op.add_column("ideas", sa.Column("checklist_data", sa.Text(), nullable=True))


def downgrade():
    # Remove checklist_data column from ideas
    op.drop_column("ideas", "checklist_data")

    # Drop daily_stats table
    op.drop_index("ix_daily_stats_user_date", table_name="daily_stats")
    op.drop_table("daily_stats")
