"""
Note model with categories and types for journaling and note-taking
"""
from datetime import datetime

from extensions import db


class NoteCategory(db.Model):
    """User-defined categories for notes"""

    __tablename__ = "note_categories"
    __table_args__ = (
        db.Index("ix_note_categories_user", "user_id"),
        {"sqlite_autoincrement": True},
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    notes = db.relationship("Note", backref="category_ref", lazy=True)

    def __repr__(self) -> str:
        return f"<NoteCategory {self.id}: {self.name}>"


class Note(db.Model):
    """Note model for journaling and note-taking"""

    __tablename__ = "notes"
    __table_args__ = (
        db.Index("ix_notes_user_updated", "user_id", "updated_at"),
        db.Index("ix_notes_user_type", "user_id", "note_type"),
        db.Index("ix_notes_user_date", "user_id", "entry_date"),
        {"sqlite_autoincrement": True},
    )

    # Note types
    TYPE_INSTRUCTIONS = "instructions"
    TYPE_REFLECTIONS = "reflections"
    TYPE_SUMMARIES = "summaries"
    TYPE_JOURNAL = "journal"
    TYPE_WEEKLY = "weekly"

    TYPES = [
        (TYPE_INSTRUCTIONS, "Instructions"),
        (TYPE_REFLECTIONS, "Reflections"),
        (TYPE_SUMMARIES, "Summaries"),
        (TYPE_JOURNAL, "Journal"),
        (TYPE_WEEKLY, "Weekly Reflection"),
    ]

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=True)
    note_type = db.Column(db.String(50), nullable=False, default=TYPE_JOURNAL)
    category_id = db.Column(
        db.Integer, db.ForeignKey("note_categories.id"), nullable=True
    )
    entry_date = db.Column(db.Date, nullable=True)  # For journal/weekly entries
    pinned = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Note {self.id}: {self.title}>"

    @property
    def type_display(self) -> str:
        """Get human-readable type name"""
        for type_val, type_name in self.TYPES:
            if type_val == self.note_type:
                return type_name
        return self.note_type.title()

    @property
    def snippet(self) -> str:
        """Get first 120 chars of content"""
        if not self.content:
            return ""
        return self.content[:120] + ("..." if len(self.content) > 120 else "")

    @classmethod
    def get_type_choices(cls) -> list[tuple[str, str]]:
        """Get type choices for forms"""
        return cls.TYPES
