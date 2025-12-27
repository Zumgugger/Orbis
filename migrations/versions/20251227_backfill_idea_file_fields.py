"""Backfill idea_files normalized columns from legacy fields

Revision ID: 20251227_backfill_idea_file_fields
Revises: 20251227_add_ideas_metadata_columns
Create Date: 2025-12-27
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20251227_backfill_idea_file_fields"
down_revision = "20251227_add_ideas_metadata_columns"
branch_labels = None
depends_on = None


def upgrade():
    # Populate normalized columns from legacy ones where missing
    op.execute(
        """
        UPDATE idea_files
        SET original_filename = COALESCE(original_filename, filename),
            stored_filename   = COALESCE(stored_filename, filename),
            file_path         = COALESCE(file_path, filepath),
            file_size         = COALESCE(file_size, filesize),
            mime_type         = mime_type
        """
    )


def downgrade():
    # No data rollback; leave normalized columns as-is
    pass
