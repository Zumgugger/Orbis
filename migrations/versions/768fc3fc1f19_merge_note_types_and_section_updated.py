"""merge_note_types_and_section_updated

Revision ID: 768fc3fc1f19
Revises: 20260101_add_section_updated_at, 20260107_add_note_types
Create Date: 2026-01-07 23:29:21.978546

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "768fc3fc1f19"
down_revision = ("20260101_add_section_updated_at", "20260107_add_note_types")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
