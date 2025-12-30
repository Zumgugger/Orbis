"""
Database initialization and migration utilities
Models are defined in the models/ package
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from extensions import db

# Re-export all models for backward compatibility
from models import (
    CompletionLog,
    Daily,
    Goal,
    Habit,
    Idea,
    IdeaFile,
    MasterCategory,
    MasterSection,
    Milestone,
    RolloverState,
    ShoppingList,
    Todo,
    User,
)

if TYPE_CHECKING:
    from flask import Flask


def init_db(app: Flask) -> None:
    """Initialize database with Flask app"""
    db.init_app(app)
    with app.app_context():
        db.create_all()
        # Legacy migrations for backward compatibility
        # New schema changes should use: flask db migrate && flask db upgrade
        _apply_legacy_migrations()


def _apply_legacy_migrations() -> None:
    """Legacy migrations applied at startup for backward compatibility.

    DEPRECATED: New schema changes should use Alembic migrations:
        flask db migrate -m "description"
        flask db upgrade

    These inline migrations exist only for databases created before
    Alembic was adopted. They will be removed in a future version.
    """
    try:
        engine = db.engine  # Use db.engine instead of deprecated get_engine()
        inspector = db.inspect(engine)

        # Goals table migrations
        goal_columns = {col["name"] for col in inspector.get_columns("goals")}
        with engine.connect() as conn:
            if "deadline" not in goal_columns:
                conn.execute(db.text("ALTER TABLE goals ADD COLUMN deadline DATE"))
                conn.commit()
            if "position" not in goal_columns:
                conn.execute(
                    db.text("ALTER TABLE goals ADD COLUMN position INTEGER DEFAULT 0")
                )
                conn.commit()

        # Dailies table migrations
        daily_columns = {col["name"] for col in inspector.get_columns("dailies")}
        with engine.connect() as conn:
            if "repeat_limit" not in daily_columns:
                conn.execute(
                    db.text("ALTER TABLE dailies ADD COLUMN repeat_limit INTEGER")
                )
                conn.commit()
            if "exercise_minutes" not in daily_columns:
                conn.execute(
                    db.text("ALTER TABLE dailies ADD COLUMN exercise_minutes INTEGER")
                )
                conn.commit()
            if "position" not in daily_columns:
                conn.execute(
                    db.text("ALTER TABLE dailies ADD COLUMN position INTEGER DEFAULT 0")
                )
                conn.commit()

        # Ideas table migrations
        idea_columns = {col["name"] for col in inspector.get_columns("ideas")}
        with engine.connect() as conn:
            if "position" not in idea_columns:
                conn.execute(
                    db.text("ALTER TABLE ideas ADD COLUMN position INTEGER DEFAULT 0")
                )
                conn.commit()

        # Cleanup orphaned idea files
        try:
            with engine.connect() as conn:
                conn.execute(
                    db.text(
                        "DELETE FROM idea_files WHERE idea_id NOT IN (SELECT id FROM ideas)"
                    )
                )
                conn.commit()
        except Exception:
            pass

        # Shopping lists table migrations
        shopping_columns = {
            col["name"] for col in inspector.get_columns("shopping_lists")
        }
        with engine.connect() as conn:
            if "position" not in shopping_columns:
                conn.execute(
                    db.text(
                        "ALTER TABLE shopping_lists ADD COLUMN position INTEGER DEFAULT 0"
                    )
                )
                conn.commit()

        # Todos table migrations
        todo_columns = {col["name"] for col in inspector.get_columns("todos")}
        with engine.connect() as conn:
            if "position" not in todo_columns:
                conn.execute(
                    db.text("ALTER TABLE todos ADD COLUMN position INTEGER DEFAULT 0")
                )
                conn.commit()

    except Exception:
        # Avoid blocking app startup if inspection fails
        pass


__all__ = [
    "db",
    "init_db",
    "User",
    "RolloverState",
    "Todo",
    "Daily",
    "CompletionLog",
    "Habit",
    "Goal",
    "Milestone",
    "ShoppingList",
    "Idea",
    "IdeaFile",
    "MasterCategory",
    "MasterSection",
]
