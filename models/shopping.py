"""
Shopping list model
"""
from datetime import datetime

from extensions import db


class ShoppingList(db.Model):
    """Shopping list model with title and text-based items"""

    __tablename__ = "shopping_lists"
    __table_args__ = (
        db.Index("ix_shopping_lists_user_updated", "user_id", "updated_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    items = db.Column(db.Text, nullable=True)  # Text field for list items
    position = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<ShoppingList {self.id}: {self.title}>"

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "items": self.items,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
