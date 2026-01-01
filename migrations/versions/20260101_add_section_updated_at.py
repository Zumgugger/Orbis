"""Add updated_at column to master_sections

Revision ID: 20260101_add_section_updated_at
Revises:
Create Date: 2026-01-01

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260101_add_section_updated_at"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add updated_at column to master_sections
    with op.batch_alter_table("master_sections", schema=None) as batch_op:
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))

    # Set initial updated_at values to created_at for existing rows
    op.execute(
        "UPDATE master_sections SET updated_at = created_at WHERE updated_at IS NULL"
    )


def downgrade():
    with op.batch_alter_table("master_sections", schema=None) as batch_op:
        batch_op.drop_column("updated_at")
