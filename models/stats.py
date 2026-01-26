"""
Statistics tracking models for historical progress data
"""
from datetime import date, datetime

from extensions import db


class DailyStats(db.Model):
    """Track daily completion statistics for each user"""

    __tablename__ = "daily_stats"
    __table_args__ = (
        db.Index("ix_daily_stats_user_date", "user_id", "stat_date"),
        db.UniqueConstraint("user_id", "stat_date", name="uq_daily_stats_user_date"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    stat_date = db.Column(db.Date, nullable=False, default=date.today)

    # Completion counts
    todos_completed = db.Column(db.Integer, default=0)
    todos_total = db.Column(db.Integer, default=0)
    dailies_completed = db.Column(db.Integer, default=0)
    dailies_total = db.Column(db.Integer, default=0)
    habits_completed = db.Column(db.Integer, default=0)
    habits_total = db.Column(db.Integer, default=0)

    # Overall stats
    total_completed = db.Column(db.Integer, default=0)
    total_items = db.Column(db.Integer, default=0)
    completion_percentage = db.Column(db.Integer, default=0)  # 0-100

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<DailyStats user={self.user_id} date={self.stat_date} {self.completion_percentage}%>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "stat_date": self.stat_date.isoformat() if self.stat_date else None,
            "todos_completed": self.todos_completed,
            "todos_total": self.todos_total,
            "dailies_completed": self.dailies_completed,
            "dailies_total": self.dailies_total,
            "habits_completed": self.habits_completed,
            "habits_total": self.habits_total,
            "total_completed": self.total_completed,
            "total_items": self.total_items,
            "completion_percentage": self.completion_percentage,
        }

    @property
    def is_perfect_day(self) -> bool:
        """Check if this was a 100% completion day"""
        return self.completion_percentage == 100 and self.total_items > 0

    @classmethod
    def get_or_create(cls, user_id: int, stat_date: date) -> "DailyStats":
        """Get existing stats for date or create new entry"""
        stats = cls.query.filter_by(user_id=user_id, stat_date=stat_date).first()
        if not stats:
            stats = cls(user_id=user_id, stat_date=stat_date)
            db.session.add(stats)
        return stats

    @classmethod
    def get_perfect_days_count(cls, user_id: int) -> int:
        """Get count of 100% completion days for user"""
        return cls.query.filter(
            cls.user_id == user_id,
            cls.completion_percentage == 100,
            cls.total_items > 0,
        ).count()

    @classmethod
    def get_current_streak(cls, user_id: int) -> int:
        """Get current streak of consecutive days with >= 80% completion"""
        from sqlalchemy import desc

        stats = (
            cls.query.filter(cls.user_id == user_id, cls.total_items > 0)
            .order_by(desc(cls.stat_date))
            .all()
        )

        if not stats:
            return 0

        streak = 0
        expected_date = date.today()

        for stat in stats:
            # Allow for today not being recorded yet
            if stat.stat_date == expected_date or stat.stat_date == expected_date:
                if stat.completion_percentage >= 80:
                    streak += 1
                    expected_date = stat.stat_date - __import__("datetime").timedelta(
                        days=1
                    )
                else:
                    break
            elif stat.stat_date < expected_date:
                # Gap in dates - check if it's just one day behind
                days_diff = (expected_date - stat.stat_date).days
                if days_diff == 1 and stat.completion_percentage >= 80:
                    streak += 1
                    expected_date = stat.stat_date - __import__("datetime").timedelta(
                        days=1
                    )
                else:
                    break

        return streak

    @classmethod
    def get_best_streak(cls, user_id: int) -> int:
        """Get best streak of consecutive days with >= 80% completion"""
        from sqlalchemy import asc

        stats = (
            cls.query.filter(cls.user_id == user_id, cls.total_items > 0)
            .order_by(asc(cls.stat_date))
            .all()
        )

        if not stats:
            return 0

        best_streak = 0
        current_streak = 0
        prev_date = None

        for stat in stats:
            if stat.completion_percentage >= 80:
                if prev_date is None or (stat.stat_date - prev_date).days == 1:
                    current_streak += 1
                else:
                    current_streak = 1
                best_streak = max(best_streak, current_streak)
            else:
                current_streak = 0
            prev_date = stat.stat_date

        return best_streak

    @classmethod
    def get_average_completion(cls, user_id: int, days: int = 30) -> float:
        """Get average completion percentage over last N days"""
        from datetime import timedelta

        from sqlalchemy import func

        cutoff = date.today() - timedelta(days=days)
        result = (
            db.session.query(func.avg(cls.completion_percentage))
            .filter(
                cls.user_id == user_id, cls.stat_date >= cutoff, cls.total_items > 0
            )
            .scalar()
        )

        return round(result or 0, 1)
