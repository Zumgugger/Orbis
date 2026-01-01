"""
SharedTitle model for frequently used shared calendar block titles
"""
from datetime import datetime

from extensions import db


class SharedTitle(db.Model):
    """Frequently used titles for shared calendar blocks"""

    __tablename__ = "shared_titles"
    __table_args__ = (
        db.Index("ix_shared_titles_user", "user_id"),
        db.UniqueConstraint("user_id", "title", name="uq_shared_titles_user_title"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(50), nullable=False)
    is_default_work_hours = db.Column(
        db.Boolean, default=False
    )  # Auto-select for 7:00-17:30
    position = db.Column(db.Integer, default=0)  # For ordering in dropdown
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("shared_titles", lazy="dynamic"))

    def __repr__(self) -> str:
        return f"<SharedTitle {self.id}: {self.title}>"

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "is_default_work_hours": self.is_default_work_hours,
            "position": self.position,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def get_default_titles(cls) -> list[dict]:
        """Get the default shared titles to seed for new users"""
        return [
            {"title": "Work", "is_default_work_hours": True, "position": 0},
            {"title": "Sitzung", "is_default_work_hours": False, "position": 1},
            {"title": "Musik", "is_default_work_hours": False, "position": 2},
            {"title": "Konzert", "is_default_work_hours": False, "position": 3},
        ]

    @classmethod
    def seed_for_user(cls, user_id: int) -> list["SharedTitle"]:
        """Create default shared titles for a user"""
        titles = []
        for default in cls.get_default_titles():
            # Check if already exists
            existing = cls.query.filter_by(
                user_id=user_id, title=default["title"]
            ).first()
            if not existing:
                title = cls(user_id=user_id, **default)
                db.session.add(title)
                titles.append(title)
        if titles:
            db.session.commit()
        return titles
