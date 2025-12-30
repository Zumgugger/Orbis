"""
Goal tracking model with milestones
"""
from datetime import datetime

from extensions import db


class Goal(db.Model):
    """Goal tracking model with milestones"""

    __tablename__ = "goals"
    __table_args__ = (db.Index("ix_goals_user_status", "user_id", "status"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="active")  # active, completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    deadline = db.Column(db.Date, nullable=True)
    position = db.Column(db.Integer, default=0)

    # Relationship to milestones
    milestones = db.relationship(
        "Milestone", backref="goal", lazy=True, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Goal {self.id}: {self.title}>"

    def get_completed_milestones_count(self) -> int:
        """Get count of completed milestones"""
        return sum(1 for m in self.milestones if m.completed)

    def get_total_milestones_count(self) -> int:
        """Get total count of milestones"""
        return len(self.milestones)

    def get_progress_percentage(self) -> float:
        """Calculate progress percentage based on milestones"""
        total = self.get_total_milestones_count()
        if total == 0:
            return 0
        completed = self.get_completed_milestones_count()
        return (completed / total) * 100

    def is_completed(self) -> bool:
        """Check if all milestones are completed"""
        if not self.milestones:
            return False
        return all(m.completed for m in self.milestones)

    def update_status(self) -> None:
        """Update goal status based on milestone completion"""
        if self.is_completed() and self.status != "completed":
            self.status = "completed"
            self.completed_at = datetime.utcnow()
        elif not self.is_completed() and self.status == "completed":
            self.status = "active"
            self.completed_at = None

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "milestones": [m.to_dict() for m in self.milestones],
            "progress_percentage": self.get_progress_percentage(),
        }


class Milestone(db.Model):
    """Milestone model for goals"""

    __tablename__ = "milestones"
    __table_args__ = (db.Index("ix_milestones_goal_id", "goal_id"),)

    id = db.Column(db.Integer, primary_key=True)
    goal_id = db.Column(db.Integer, db.ForeignKey("goals.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    order = db.Column(db.Integer, default=0)  # For ordering milestones
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Milestone {self.id}: {self.title}>"

    def toggle_completion(self) -> None:
        """Toggle milestone completion status"""
        self.completed = not self.completed

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "goal_id": self.goal_id,
            "title": self.title,
            "completed": self.completed,
            "order": self.order,
            "created_at": self.created_at.isoformat(),
        }
