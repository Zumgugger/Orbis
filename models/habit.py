"""
Habit tracking model with positive/negative counters and logging
"""
from datetime import date, datetime, timedelta

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
    best_streak = db.Column(db.Integer, default=0)  # Best consecutive days with increments
    current_streak = db.Column(db.Integer, default=0)  # Current consecutive days

    # Relationship to logs
    logs = db.relationship("HabitLog", backref="habit", lazy="dynamic", cascade="all, delete-orphan")

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

    def increment(self, target_date: date | None = None) -> "HabitLog":
        """Increment count by 1 for the given date (defaults to today). Returns the log entry."""
        target = target_date or date.today()
        self.count += 1
        self.last_increment_date = target
        self._update_streak(target)
        
        # Create log entry
        log = HabitLog(
            habit_id=self.id,
            user_id=self.user_id,
            delta=1,
            logged_date=target,
            count_after=self.count
        )
        db.session.add(log)
        return log

    def decrement(self, target_date: date | None = None) -> "HabitLog":
        """Decrement count by 1. Returns the log entry."""
        target = target_date or date.today()
        self.count -= 1
        
        # Create log entry
        log = HabitLog(
            habit_id=self.id,
            user_id=self.user_id,
            delta=-1,
            logged_date=target,
            count_after=self.count
        )
        db.session.add(log)
        return log

    def _update_streak(self, target_date: date) -> None:
        """Update streak counters based on the increment date."""
        yesterday = target_date - timedelta(days=1)
        
        if self.last_increment_date == yesterday or self.last_increment_date == target_date:
            # Continuing or same day - increment streak
            if self.last_increment_date != target_date:
                self.current_streak = (self.current_streak or 0) + 1
        elif self.last_increment_date is None:
            # First ever increment
            self.current_streak = 1
        else:
            # Gap in days - reset streak
            self.current_streak = 1
        
        # Update best streak
        if (self.current_streak or 0) > (self.best_streak or 0):
            self.best_streak = self.current_streak

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
            "best_streak": self.best_streak or 0,
            "current_streak": self.current_streak or 0,
        }


class HabitLog(db.Model):
    """Log of habit increments/decrements for tracking history and trends"""

    __tablename__ = "habit_logs"
    __table_args__ = (
        db.Index("ix_habit_logs_user_date", "user_id", "logged_date"),
        db.Index("ix_habit_logs_habit_date", "habit_id", "logged_date"),
    )

    id = db.Column(db.Integer, primary_key=True)
    habit_id = db.Column(db.Integer, db.ForeignKey("habits.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    delta = db.Column(db.Integer, nullable=False)  # +1 for increment, -1 for decrement
    logged_date = db.Column(db.Date, nullable=False)
    count_after = db.Column(db.Integer, nullable=False)  # Count after this action
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<HabitLog {self.habit_id} delta={self.delta} on {self.logged_date}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "habit_id": self.habit_id,
            "delta": self.delta,
            "logged_date": self.logged_date.isoformat(),
            "count_after": self.count_after,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
