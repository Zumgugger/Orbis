"""
Idea model with notes, mindmaps, and file attachments
"""
import json
from datetime import datetime

from extensions import db


class Idea(db.Model):
    """Idea model for storing ideas with notes, mindmaps, and files"""

    __tablename__ = "ideas"
    __table_args__ = (
        db.Index("ix_ideas_user_updated", "user_id", "updated_at"),
        {"sqlite_autoincrement": True},  # prevent ID reuse on SQLite
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)  # Markdown notes
    mindmap_data = db.Column(db.Text, nullable=True)  # JSON mindmap data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    position = db.Column(db.Integer, default=0)

    files = db.relationship(
        "IdeaFile", backref="idea", lazy=True, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Idea {self.id}: {self.title}>"

    def get_mindmap_data(self) -> dict | None:
        """Get mindmap data as dict"""
        if not self.mindmap_data:
            return None
        try:
            return json.loads(self.mindmap_data)
        except Exception:
            return None

    def set_mindmap_data(self, data: dict | str) -> None:
        """Set mindmap data from dict"""
        try:
            self.mindmap_data = json.dumps(data) if isinstance(data, dict) else data
        except Exception:
            self.mindmap_data = data


class IdeaFile(db.Model):
    """File attachments for ideas"""

    __tablename__ = "idea_files"
    __table_args__ = (db.Index("ix_idea_files_idea_id", "idea_id"),)

    id = db.Column(db.Integer, primary_key=True)
    idea_id = db.Column(
        db.Integer, db.ForeignKey("ideas.id", ondelete="CASCADE"), nullable=False
    )
    # New fields expected by tests
    original_filename = db.Column(db.String(255), nullable=True)
    stored_filename = db.Column(db.String(255), nullable=True)
    file_path = db.Column(db.String(500), nullable=True)
    file_size = db.Column(db.Integer, nullable=True)
    mime_type = db.Column(db.String(100), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        name = self.original_filename or "unnamed"
        return f"<IdeaFile {self.id}: {name}>"
