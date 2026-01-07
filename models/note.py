"""
Note model with types for journaling and note-taking
"""
from datetime import datetime

from extensions import db


class NoteType(db.Model):
    """User-defined note types (tabs)"""

    __tablename__ = "note_types"
    __table_args__ = (
        db.Index("ix_note_types_user", "user_id"),
        db.UniqueConstraint("user_id", "name", name="uq_note_type_user_name"),
        {"sqlite_autoincrement": True},
    )

    # Built-in type slugs (used for default creation)
    BUILTIN_TYPES = ["journal", "health", "learned", "instructions"]

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    icon = db.Column(db.String(50), default="bi-file-text")  # Bootstrap icon class
    position = db.Column(db.Integer, default=0)  # For ordering tabs
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    notes = db.relationship("Note", backref="type_ref", lazy=True)

    def __repr__(self) -> str:
        return f"<NoteType {self.id}: {self.name}>"

    @classmethod
    def get_or_create_defaults(cls, user_id: int) -> list["NoteType"]:
        """Get user's note types, creating defaults if none exist"""
        existing = cls.query.filter_by(user_id=user_id).order_by(cls.position).all()
        if existing:
            return existing

        # Create default types
        defaults = [
            ("Journal", "bi-journal-text", 0),
            ("Health", "bi-heart-pulse", 1),
            ("Learned", "bi-lightbulb", 2),
            ("Instructions", "bi-list-check", 3),
        ]
        for name, icon, pos in defaults:
            nt = cls(user_id=user_id, name=name, icon=icon, position=pos)
            db.session.add(nt)
        db.session.commit()
        return cls.query.filter_by(user_id=user_id).order_by(cls.position).all()


# Keep NoteCategory for backwards compatibility but deprecate
class NoteCategory(db.Model):
    """DEPRECATED - User-defined categories for notes"""

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
        db.Index("ix_notes_user_type_id", "user_id", "note_type_id"),
        db.Index("ix_notes_user_date", "user_id", "entry_date"),
        {"sqlite_autoincrement": True},
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=True)
    # Legacy field - kept for migration, default to empty string for backwards compat
    note_type = db.Column(db.String(50), nullable=False, default="")
    # New foreign key to NoteType
    note_type_id = db.Column(db.Integer, db.ForeignKey("note_types.id"), nullable=True)
    # Legacy field - kept for migration
    category_id = db.Column(
        db.Integer, db.ForeignKey("note_categories.id"), nullable=True
    )
    entry_date = db.Column(db.Date, nullable=True)
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
        if self.type_ref:
            return self.type_ref.name
        # Fallback to legacy note_type
        if self.note_type:
            return self.note_type.title()
        return "Note"

    @property
    def snippet(self) -> str:
        """Get first 120 chars of content"""
        if not self.content:
            return ""
        return self.content[:120] + ("..." if len(self.content) > 120 else "")
