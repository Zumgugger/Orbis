"""
Test factories for creating model instances with sensible defaults.

Usage:
    from tests.factories import UserFactory, TodoFactory

    user = UserFactory.create()
    todo = TodoFactory.create(user_id=user.id, title="Custom Title")
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from database import db
from models import (
    Daily,
    Goal,
    Habit,
    Idea,
    IdeaFile,
    Milestone,
    ShoppingList,
    Todo,
    User,
)


class BaseFactory:
    """Base factory with common creation logic."""

    model = None
    defaults: dict[str, Any] = {}
    _counter = 0

    @classmethod
    def _get_counter(cls) -> int:
        cls._counter += 1
        return cls._counter

    @classmethod
    def build(cls, **kwargs) -> Any:
        """Build a model instance without saving to database."""
        attrs = {**cls.defaults, **kwargs}
        # Process any callable defaults
        for key, value in attrs.items():
            if callable(value):
                attrs[key] = value()
        return cls.model(**attrs)

    @classmethod
    def create(cls, **kwargs) -> Any:
        """Create and save a model instance to database."""
        instance = cls.build(**kwargs)
        db.session.add(instance)
        db.session.commit()
        db.session.refresh(instance)
        return instance

    @classmethod
    def create_batch(cls, count: int, **kwargs) -> list[Any]:
        """Create multiple instances."""
        return [cls.create(**kwargs) for _ in range(count)]


class UserFactory(BaseFactory):
    """Factory for User model."""

    model = User
    defaults = {
        "google_id": lambda: f"google_{UserFactory._get_counter()}",
        "email": lambda: f"user{UserFactory._get_counter()}@test.com",
        "name": lambda: f"Test User {UserFactory._get_counter()}",
        "profile_pic": "https://example.com/pic.jpg",
        "role": "user",
    }

    @classmethod
    def create_admin(cls, **kwargs) -> User:
        """Create an admin user."""
        return cls.create(role="admin", **kwargs)


class TodoFactory(BaseFactory):
    """Factory for Todo model."""

    model = Todo
    defaults = {
        "title": lambda: f"Todo {TodoFactory._get_counter()}",
        "description": "Test description",
        "priority": "medium",
        "status": "pending",
        "due_date": lambda: date.today(),
    }

    @classmethod
    def create_completed(cls, **kwargs) -> Todo:
        """Create a completed todo."""
        return cls.create(status="completed", completed_at=datetime.utcnow(), **kwargs)

    @classmethod
    def create_overdue(cls, **kwargs) -> Todo:
        """Create an overdue todo."""
        return cls.create(due_date=date.today() - timedelta(days=1), **kwargs)


class DailyFactory(BaseFactory):
    """Factory for Daily model."""

    model = Daily
    defaults = {
        "title": lambda: f"Daily {DailyFactory._get_counter()}",
        "description": "Test daily description",
        "frequency": "daily",
        "frequency_interval": 1,
        "streak_count": 0,
        "total_completions": 0,
    }

    @classmethod
    def create_weekly(cls, weekdays: list[str] = None, **kwargs) -> Daily:
        """Create a weekly daily task."""
        import json

        weekdays = weekdays or ["monday", "wednesday", "friday"]
        return cls.create(frequency="custom", weekdays=json.dumps(weekdays), **kwargs)


class HabitFactory(BaseFactory):
    """Factory for Habit model."""

    model = Habit
    defaults = {
        "title": lambda: f"Habit {HabitFactory._get_counter()}",
        "description": "Test habit description",
        "difficulty": "medium",
        "positive_count": 0,
        "negative_count": 0,
        "focused": False,
    }

    @classmethod
    def create_focused(cls, **kwargs) -> Habit:
        """Create a focused habit."""
        return cls.create(focused=True, **kwargs)


class GoalFactory(BaseFactory):
    """Factory for Goal model."""

    model = Goal
    defaults = {
        "title": lambda: f"Goal {GoalFactory._get_counter()}",
        "description": "Test goal description",
        "status": "active",
    }

    @classmethod
    def create_with_milestones(cls, milestone_count: int = 3, **kwargs) -> Goal:
        """Create a goal with milestones."""
        goal = cls.create(**kwargs)
        for i in range(milestone_count):
            MilestoneFactory.create(goal_id=goal.id, title=f"Milestone {i + 1}")
        db.session.refresh(goal)
        return goal


class MilestoneFactory(BaseFactory):
    """Factory for Milestone model."""

    model = Milestone
    defaults = {
        "title": lambda: f"Milestone {MilestoneFactory._get_counter()}",
        "completed": False,
    }


class IdeaFactory(BaseFactory):
    """Factory for Idea model."""

    model = Idea
    defaults = {
        "title": lambda: f"Idea {IdeaFactory._get_counter()}",
        "description": "Test idea description",
        "notes": "",
        "mindmap_data": "{}",
    }

    @classmethod
    def create_with_notes(cls, notes: str = "Some notes", **kwargs) -> Idea:
        """Create an idea with notes."""
        return cls.create(notes=notes, **kwargs)


class IdeaFileFactory(BaseFactory):
    """Factory for IdeaFile model."""

    model = IdeaFile
    defaults = {
        "original_filename": lambda: f"file_{IdeaFileFactory._get_counter()}.txt",
        "stored_filename": lambda: f"stored_{IdeaFileFactory._get_counter()}.txt",
        "file_path": "/uploads/test/file.txt",
        "file_size": 1024,
        "mime_type": "text/plain",
    }


class ShoppingListFactory(BaseFactory):
    """Factory for ShoppingList model."""

    model = ShoppingList
    defaults = {
        "title": lambda: f"Shopping List {ShoppingListFactory._get_counter()}",
        "items": "- Item 1\n- Item 2\n- Item 3",
    }


# Convenience function to reset all factory counters
def reset_factories():
    """Reset all factory counters. Useful between test runs."""
    for factory in [
        UserFactory,
        TodoFactory,
        DailyFactory,
        HabitFactory,
        GoalFactory,
        MilestoneFactory,
        IdeaFactory,
        IdeaFileFactory,
        ShoppingListFactory,
    ]:
        factory._counter = 0
