"""Merge multiple heads

Revision ID: 20260126_merge_heads
Revises: 20251231_add_notes_module, 20251231_add_streak_features, 20260126_add_stats_checklist
Create Date: 2026-01-26

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260126_merge_heads"
down_revision = (
    "20251231_add_notes_module",
    "20251231_add_streak_features",
    "20260126_add_stats_checklist",
)
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
