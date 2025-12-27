"""Drop legacy file columns from idea_files

Revision ID: 20251227_drop_idea_file_legacy_columns
Revises: 20251227_backfill_idea_file_fields
Create Date: 2025-12-27
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20251227_drop_idea_file_legacy_columns"
down_revision = "20251227_backfill_idea_file_fields"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("idea_files"):
        cols = {col["name"] for col in insp.get_columns("idea_files")}
        with op.batch_alter_table("idea_files") as batch:
            if "filename" in cols:
                batch.drop_column("filename")
            if "filepath" in cols:
                batch.drop_column("filepath")
            if "filesize" in cols:
                batch.drop_column("filesize")


def downgrade():
    if op.get_bind().dialect.name == "sqlite":
        # SQLite batch operations can add columns easily
        with op.batch_alter_table("idea_files") as batch:
            batch.add_column(
                sa.Column("filename", sa.String(length=255), nullable=True)
            )
            batch.add_column(
                sa.Column("filepath", sa.String(length=500), nullable=True)
            )
            batch.add_column(sa.Column("filesize", sa.Integer(), nullable=True))
    else:
        with op.batch_alter_table("idea_files") as batch:
            batch.add_column(
                sa.Column("filename", sa.String(length=255), nullable=True)
            )
            batch.add_column(
                sa.Column("filepath", sa.String(length=500), nullable=True)
            )
            batch.add_column(sa.Column("filesize", sa.Integer(), nullable=True))
