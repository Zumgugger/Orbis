"""Add ideas.category and idea_files metadata columns

Revision ID: 20251227_add_ideas_metadata_columns
Revises: 20251227_add_query_indexes
Create Date: 2025-12-27
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251227_add_ideas_metadata_columns'
down_revision = '20251227_add_query_indexes'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # Add category to ideas
    if insp.has_table('ideas'):
        cols = {col['name'] for col in insp.get_columns('ideas')}
        if 'category' not in cols:
            with op.batch_alter_table('ideas') as batch:
                batch.add_column(sa.Column('category', sa.String(length=100), nullable=True))

    # Add metadata columns to idea_files
    if insp.has_table('idea_files'):
        cols = {col['name'] for col in insp.get_columns('idea_files')}
        with op.batch_alter_table('idea_files') as batch:
            if 'original_filename' not in cols:
                batch.add_column(sa.Column('original_filename', sa.String(length=255), nullable=True))
            if 'stored_filename' not in cols:
                batch.add_column(sa.Column('stored_filename', sa.String(length=255), nullable=True))
            if 'file_path' not in cols:
                batch.add_column(sa.Column('file_path', sa.String(length=500), nullable=True))
            if 'file_size' not in cols:
                batch.add_column(sa.Column('file_size', sa.Integer(), nullable=True))
            if 'mime_type' not in cols:
                batch.add_column(sa.Column('mime_type', sa.String(length=100), nullable=True))


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table('idea_files'):
        cols = {col['name'] for col in insp.get_columns('idea_files')}
        with op.batch_alter_table('idea_files') as batch:
            if 'mime_type' in cols:
                batch.drop_column('mime_type')
            if 'file_size' in cols:
                batch.drop_column('file_size')
            if 'file_path' in cols:
                batch.drop_column('file_path')
            if 'stored_filename' in cols:
                batch.drop_column('stored_filename')
            if 'original_filename' in cols:
                batch.drop_column('original_filename')

    if insp.has_table('ideas'):
        cols = {col['name'] for col in insp.get_columns('ideas')}
        if 'category' in cols:
            with op.batch_alter_table('ideas') as batch:
                batch.drop_column('category')
