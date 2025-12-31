"""
Todo/Task model
"""
from datetime import datetime, time

from extensions import db


class Todo(db.Model):
    """Todo/Task model"""

    __tablename__ = "todos"
    __table_args__ = (
        db.Index("ix_todos_user_status_due", "user_id", "status", "due_date"),
        db.Index("ix_todos_user_due", "user_id", "due_date"),
        db.Index("ix_todos_user_due_time", "user_id", "due_date", "due_time"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="pending")  # pending, completed
    priority = db.Column(db.String(20), default="medium")  # low, medium, high
    due_date = db.Column(db.Date, nullable=True)
    due_time = db.Column(db.Time, nullable=True)  # Optional scheduled start time
    end_time = db.Column(db.Time, nullable=True)  # Optional scheduled end time
    duration_minutes = db.Column(db.Integer, nullable=True)  # Estimated duration
    google_event_id = db.Column(db.String(255), nullable=True)  # Linked calendar event
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    position = db.Column(db.Integer, default=0)

    def __repr__(self) -> str:
        return f"<Todo {self.id}: {self.title}>"

    def get_time_label(self) -> str:
        """Get formatted time label for display"""
        if not self.due_time:
            return ""

        time_str = self.due_time.strftime("%H:%M")
        if self.end_time:
            time_str += f" – {self.end_time.strftime('%H:%M')}"
        elif self.duration_minutes:
            time_str += f" ({self.get_duration_display()})"
        return time_str

    def get_duration_display(self) -> str:
        """Get human-readable duration display"""
        if not self.duration_minutes:
            return ""
        hours = self.duration_minutes // 60
        minutes = self.duration_minutes % 60
        if hours and minutes:
            return f"{hours}h {minutes}m"
        elif hours:
            return f"{hours}h"
        else:
            return f"{minutes}m"

    def get_sort_key(self) -> tuple:
        """Get sort key for chronological ordering (time-based todos first)"""
        # Todos with times sort first, then by time
        # Todos without times sort last, then by position
        if self.due_time:
            return (0, self.due_time, self.position)
        else:
            return (1, time(23, 59, 59), self.position)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "due_time": self.due_time.isoformat() if self.due_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_minutes": self.duration_minutes,
            "google_event_id": self.google_event_id,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
        }
