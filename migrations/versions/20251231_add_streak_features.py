"""Add streak freeze and best streak fields to dailies

Revision ID: 20251231_add_streak_features
Revises:
Create Date: 2025-12-31
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20251231_add_streak_features"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to dailies table
    op.add_column("dailies", sa.Column("best_streak", sa.Integer(), nullable=True))
    op.add_column(
        "dailies", sa.Column("streak_freezes_used", sa.Integer(), nullable=True)
    )
    op.add_column(
        "dailies", sa.Column("streak_freezes_month", sa.Integer(), nullable=True)
    )


def downgrade():
    op.drop_column("dailies", "streak_freezes_month")
    op.drop_column("dailies", "streak_freezes_used")
    op.drop_column("dailies", "best_streak")
