"""merge_multiple_heads

Revision ID: d2282fc449a4
Revises: 20251231_add_notes_module, 20251231_add_streak_features, 20260101_add_dual_calendar
Create Date: 2026-01-01 19:07:11.019136

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d2282fc449a4"
down_revision = (
    "20251231_add_notes_module",
    "20251231_add_streak_features",
    "20260101_add_dual_calendar",
)
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
