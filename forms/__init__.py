"""
Flask-WTF form classes for Orbis application.
"""
from forms.daily_forms import DailyCreateForm, DailyEditForm
from forms.goal_forms import GoalCreateForm, GoalEditForm, MilestoneForm
from forms.habit_forms import HabitCreateForm, HabitEditForm
from forms.idea_forms import IdeaCreateForm, IdeaEditForm
from forms.shopping_forms import ShoppingListForm
from forms.todo_forms import TodoCreateForm, TodoEditForm

__all__ = [
    "TodoCreateForm",
    "TodoEditForm",
    "DailyCreateForm",
    "DailyEditForm",
    "HabitCreateForm",
    "HabitEditForm",
    "GoalCreateForm",
    "GoalEditForm",
    "MilestoneForm",
    "IdeaCreateForm",
    "IdeaEditForm",
    "ShoppingListForm",
]
