"""Add supporting indexes for query hygiene

Revision ID: 20251227_add_query_indexes
Revises: 20251227_add_missing_columns
Create Date: 2025-12-27
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251227_add_query_indexes'
down_revision = '20251227_add_missing_columns'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    def _has_index(table_name, index_name):
        if not insp.has_table(table_name):
            return True
        return any(idx.get('name') == index_name for idx in insp.get_indexes(table_name))

    if not _has_index('todos', 'ix_todos_user_status_due'):
        op.create_index('ix_todos_user_status_due', 'todos', ['user_id', 'status', 'due_date'])
    if not _has_index('todos', 'ix_todos_user_due'):
        op.create_index('ix_todos_user_due', 'todos', ['user_id', 'due_date'])

    if not _has_index('dailies', 'ix_dailies_user_id'):
        op.create_index('ix_dailies_user_id', 'dailies', ['user_id'])

    if not _has_index('habits', 'ix_habits_user_focus_pos'):
        op.create_index('ix_habits_user_focus_pos', 'habits', ['user_id', 'focused', 'position'])

    if not _has_index('goals', 'ix_goals_user_status'):
        op.create_index('ix_goals_user_status', 'goals', ['user_id', 'status'])

    if not _has_index('milestones', 'ix_milestones_goal_id'):
        op.create_index('ix_milestones_goal_id', 'milestones', ['goal_id'])

    if not _has_index('shopping_lists', 'ix_shopping_lists_user_updated'):
        op.create_index('ix_shopping_lists_user_updated', 'shopping_lists', ['user_id', 'updated_at'])

    if not _has_index('master_categories', 'ix_master_categories_user_position'):
        op.create_index('ix_master_categories_user_position', 'master_categories', ['user_id', 'position'])

    if not _has_index('master_sections', 'ix_master_sections_cat_user_position'):
        op.create_index('ix_master_sections_cat_user_position', 'master_sections', ['category_id', 'user_id', 'position'])

    if not _has_index('ideas', 'ix_ideas_user_updated'):
        op.create_index('ix_ideas_user_updated', 'ideas', ['user_id', 'updated_at'])

    if not _has_index('idea_files', 'ix_idea_files_idea_id'):
        op.create_index('ix_idea_files_idea_id', 'idea_files', ['idea_id'])


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    def _drop_if_exists(table_name, index_name):
        if insp.has_table(table_name):
            existing = {idx.get('name') for idx in insp.get_indexes(table_name)}
            if index_name in existing:
                op.drop_index(index_name, table_name=table_name)

    _drop_if_exists('idea_files', 'ix_idea_files_idea_id')
    _drop_if_exists('ideas', 'ix_ideas_user_updated')
    _drop_if_exists('master_sections', 'ix_master_sections_cat_user_position')
    _drop_if_exists('master_categories', 'ix_master_categories_user_position')
    _drop_if_exists('shopping_lists', 'ix_shopping_lists_user_updated')
    _drop_if_exists('milestones', 'ix_milestones_goal_id')
    _drop_if_exists('goals', 'ix_goals_user_status')
    _drop_if_exists('habits', 'ix_habits_user_focus_pos')
    _drop_if_exists('dailies', 'ix_dailies_user_id')
    _drop_if_exists('todos', 'ix_todos_user_due')
    _drop_if_exists('todos', 'ix_todos_user_status_due')
