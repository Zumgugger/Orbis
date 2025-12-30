"""
Habit tracking model with positive/negative counters
"""
from datetime import date, datetime

from extensions import db


class Habit(db.Model):
    """Habit tracking model with positive/negative counters"""

    __tablename__ = "habits"
    __table_args__ = (
        db.Index("ix_habits_user_focus_pos", "user_id", "focused", "position"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    difficulty = db.Column(db.String(20), default="normal")  # easy, normal, hard
    count = db.Column(db.Integer, default=0)  # Can be positive or negative
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    position = db.Column(db.Integer, default=0)
    focused = db.Column(db.Boolean, default=False)
    last_increment_date = db.Column(db.Date, nullable=True)

    def __repr__(self) -> str:
        return f"<Habit {self.id}: {self.title}>"

    def get_max_count(self) -> int:
        """Get the maximum count for progress bar based on difficulty"""
        if self.difficulty == "easy":
            return 30
        elif self.difficulty == "hard":
            return 300
        else:  # normal
            return 100

    def get_progress_percentage(self) -> float:
        """Calculate progress percentage (capped at 100%)"""
        max_count = self.get_max_count()
        if self.count <= 0:
            return 0
        percentage = (self.count / max_count) * 100
        return min(100, percentage)

    def increment(self, target_date: date | None = None) -> None:
        """Increment count by 1 for the given date (defaults to today)."""
        self.count += 1
        self.last_increment_date = target_date or date.today()

    def decrement(self) -> None:
        """Decrement count by 1"""
        self.count -= 1

    def get_difficulty_icon(self) -> str:
        """Get Bootstrap icon for difficulty"""
        if self.difficulty == "easy":
            return "feather"
        elif self.difficulty == "hard":
            return "fire"
        else:  # normal
            return "bullseye"

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "difficulty": self.difficulty,
            "count": self.count,
            "max_count": self.get_max_count(),
            "progress_percentage": self.get_progress_percentage(),
            "created_at": self.created_at.isoformat(),
            "position": self.position,
            "focused": self.focused,
            "last_increment_date": self.last_increment_date.isoformat()
            if self.last_increment_date
            else None,
        }
