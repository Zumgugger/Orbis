"""
Masterprompt models - categories and sections for building prompts
"""
from datetime import datetime

from extensions import db


class MasterCategory(db.Model):
    """Masterprompt category per user"""

    __tablename__ = "master_categories"
    __table_args__ = (
        db.Index("ix_master_categories_user_position", "user_id", "position"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    position = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sections = db.relationship(
        "MasterSection", backref="category", lazy=True, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<MasterCategory {self.id}: {self.name}>"


class MasterSection(db.Model):
    """Reusable masterprompt section grouped by category"""

    __tablename__ = "master_sections"
    __table_args__ = (
        db.Index(
            "ix_master_sections_cat_user_position", "category_id", "user_id", "position"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(
        db.Integer, db.ForeignKey("master_categories.id"), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    position = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<MasterSection {self.id}: {self.title}>"
