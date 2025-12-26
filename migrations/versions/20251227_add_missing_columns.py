"""Add missing columns for habits and users

Revision ID: 20251227_add_missing_columns
Revises: 
Create Date: 2025-12-27
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251227_add_missing_columns'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # Habits table columns
    habit_columns = {col['name'] for col in insp.get_columns('habits')} if insp.has_table('habits') else set()
    if insp.has_table('habits'):
        with op.batch_alter_table('habits') as batch:
            if 'position' not in habit_columns:
                batch.add_column(sa.Column('position', sa.Integer(), server_default='0'))
            if 'focused' not in habit_columns:
                batch.add_column(sa.Column('focused', sa.Boolean(), server_default=sa.text('0')))
            if 'last_increment_date' not in habit_columns:
                batch.add_column(sa.Column('last_increment_date', sa.Date()))

    # Users table columns
    user_columns = {col['name'] for col in insp.get_columns('users')} if insp.has_table('users') else set()
    if insp.has_table('users') and 'oauth_token' not in user_columns:
        with op.batch_alter_table('users') as batch:
            batch.add_column(sa.Column('oauth_token', sa.Text()))

    # Remove server defaults after data backfill
    if insp.has_table('habits'):
        with op.batch_alter_table('habits') as batch:
            if 'position' not in habit_columns:
                batch.alter_column('position', server_default=None)
            if 'focused' not in habit_columns:
                batch.alter_column('focused', server_default=None)


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table('habits'):
        habit_columns = {col['name'] for col in insp.get_columns('habits')}
        with op.batch_alter_table('habits') as batch:
            if 'last_increment_date' in habit_columns:
                batch.drop_column('last_increment_date')
            if 'focused' in habit_columns:
                batch.drop_column('focused')
            if 'position' in habit_columns:
                batch.drop_column('position')

    if insp.has_table('users'):
        user_columns = {col['name'] for col in insp.get_columns('users')}
        if 'oauth_token' in user_columns:
            with op.batch_alter_table('users') as batch:
                batch.drop_column('oauth_token')
