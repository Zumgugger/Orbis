"""
Database initialization and migration utilities
Models are defined in the models/ package
"""
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


def init_db(app):
    """Initialize database with Flask app"""
    db.init_app(app)
    with app.app_context():
        db.create_all()
        apply_migrations()


def apply_migrations():
    """Lightweight migrations applied at startup.

    NOTE: These are legacy migrations for backward compatibility.
    New schema changes should use Alembic migrations in migrations/versions/
    """
    try:
        engine = db.get_engine()
        inspector = db.inspect(engine)

        goal_columns = [col["name"] for col in inspector.get_columns("goals")]
        with engine.connect() as conn:
            if "deadline" not in goal_columns:
                conn.execute(db.text("ALTER TABLE goals ADD COLUMN deadline DATE"))
            if "position" not in goal_columns:
                conn.execute(
                    db.text("ALTER TABLE goals ADD COLUMN position INTEGER DEFAULT 0")
                )

        daily_columns = [col["name"] for col in inspector.get_columns("dailies")]
        with engine.connect() as conn:
            if "repeat_limit" not in daily_columns:
                conn.execute(
                    db.text("ALTER TABLE dailies ADD COLUMN repeat_limit INTEGER")
                )
            if "exercise_minutes" not in daily_columns:
                conn.execute(
                    db.text("ALTER TABLE dailies ADD COLUMN exercise_minutes INTEGER")
                )
            if "position" not in daily_columns:
                conn.execute(
                    db.text("ALTER TABLE dailies ADD COLUMN position INTEGER DEFAULT 0")
                )

        idea_columns = [col["name"] for col in inspector.get_columns("ideas")]
        with engine.connect() as conn:
            if "position" not in idea_columns:
                conn.execute(
                    db.text("ALTER TABLE ideas ADD COLUMN position INTEGER DEFAULT 0")
                )

        # Cleanup orphaned idea files referencing non-existent ideas (from prior tests)
        try:
            with engine.connect() as conn:
                conn.execute(
                    db.text(
                        "DELETE FROM idea_files WHERE idea_id NOT IN (SELECT id FROM ideas)"
                    )
                )
        except Exception:
            pass

        # Shopping lists: ensure position exists
        shopping_columns = [
            col["name"] for col in inspector.get_columns("shopping_lists")
        ]
        with engine.connect() as conn:
            if "position" not in shopping_columns:
                conn.execute(
                    db.text(
                        "ALTER TABLE shopping_lists ADD COLUMN position INTEGER DEFAULT 0"
                    )
                )

        # Todos: ensure position exists for ordering
        todo_columns = [col["name"] for col in inspector.get_columns("todos")]
        with engine.connect() as conn:
            if "position" not in todo_columns:
                conn.execute(
                    db.text("ALTER TABLE todos ADD COLUMN position INTEGER DEFAULT 0")
                )
    except Exception:
        # Avoid blocking app startup if inspection fails
        pass


__all__ = [
    "db",
    "init_db",
    "apply_migrations",
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
