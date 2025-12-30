"""
Daily recurring task model and completion tracking
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta

from extensions import db

# Type alias for weekday names
WEEKDAY_NAMES = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]


class Daily(db.Model):
    """Daily recurring task model"""

    __tablename__ = "dailies"
    __table_args__ = (db.Index("ix_dailies_user_id", "user_id"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    streak_count = db.Column(db.Integer, default=0)
    total_completions = db.Column(db.Integer, default=0)
    last_completed_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    position = db.Column(db.Integer, default=0)

    # Optional limits and metadata
    repeat_limit = db.Column(
        db.Integer, nullable=True
    )  # Stop showing after N completions
    exercise_minutes = db.Column(
        db.Integer, nullable=True
    )  # Suggested duration per session

    # Frequency fields
    frequency = db.Column(
        db.String(20), default="daily"
    )  # daily, weekly, monthly, custom
    frequency_interval = db.Column(
        db.Integer, default=1
    )  # For daily/weekly/monthly: repeat every N units
    weekdays = db.Column(
        db.Text, nullable=True
    )  # JSON: ["monday", "wednesday", "friday"]

    def __repr__(self) -> str:
        return f"<Daily {self.id}: {self.title}>"

    # ---------- Weekday helpers ----------

    def get_weekdays(self) -> list[str]:
        """Get list of weekdays for this daily (if frequency is custom)"""
        if not self.weekdays:
            return []
        try:
            return json.loads(self.weekdays)
        except Exception:
            return []

    def set_weekdays(self, weekdays_list: list[str]) -> None:
        """Set weekdays for this daily"""
        self.weekdays = json.dumps(weekdays_list)

    # ---------- Schedule checking ----------

    def should_complete_today(self) -> bool:
        """Check if this daily should be completable today based on frequency"""
        return self.should_complete_on(date.today())

    def should_complete_on(self, target_date: date) -> bool:
        """Check if this daily should be completable on a specific date"""
        # Check if repeat limit reached
        if self._is_repeat_limit_reached():
            return False

        # Can't complete for past dates before last completion
        if self.last_completed_date and target_date < self.last_completed_date:
            return False

        return self._should_complete_by_frequency(target_date)

    def _is_repeat_limit_reached(self) -> bool:
        """Check if this daily has reached its repeat limit"""
        return (
            self.repeat_limit is not None
            and self.total_completions >= self.repeat_limit
        )

    def _should_complete_by_frequency(self, target_date: date) -> bool:
        """Determine if daily should complete based on frequency rules"""
        if self.frequency == "daily":
            return self._should_complete_daily(target_date)
        elif self.frequency == "weekly":
            return self._should_complete_weekly(target_date)
        elif self.frequency == "monthly":
            return self._should_complete_monthly(target_date)
        elif self.frequency == "custom":
            return self._should_complete_custom(target_date)
        return True

    def _should_complete_daily(self, target_date: date) -> bool:
        """Check daily frequency completion"""
        if not self.last_completed_date:
            return True
        days_since_last = (target_date - self.last_completed_date).days
        return days_since_last >= self.frequency_interval

    def _should_complete_weekly(self, target_date: date) -> bool:
        """Check weekly frequency completion"""
        if not self.last_completed_date:
            return True
        days_since_last = (target_date - self.last_completed_date).days
        return days_since_last >= (7 * self.frequency_interval)

    def _should_complete_monthly(self, target_date: date) -> bool:
        """Check monthly frequency completion"""
        if not self.last_completed_date:
            return True
        days_since_last = (target_date - self.last_completed_date).days
        return days_since_last >= (30 * self.frequency_interval)

    def _should_complete_custom(self, target_date: date) -> bool:
        """Check custom weekday frequency completion"""
        target_weekday = WEEKDAY_NAMES[target_date.weekday()]
        return target_weekday in self.get_weekdays()

    # ---------- Completion status ----------

    def is_completed_on(self, target_date: date) -> bool:
        """Check if this daily was completed on a specific date"""
        if not self.last_completed_date:
            return False
        return self.last_completed_date == target_date

    def is_completed_today(self) -> bool:
        """Check if this daily was completed today"""
        return self.is_completed_on(date.today())

    # ---------- Completion toggling ----------

    def toggle_completion(self) -> None:
        """Toggle daily completion for today and update streak/totals"""
        self.toggle_completion_on(date.today())

    def toggle_completion_on(self, target_date: date) -> None:
        """Toggle completion for a specific date (used for early scratch on Tomorrow)."""
        if not isinstance(target_date, date):
            return

        # Check repeat limit before allowing new completion
        if self._is_repeat_limit_reached() and not self.is_completed_on(target_date):
            return

        if self.is_completed_on(target_date):
            self._uncomplete(target_date)
        else:
            self._complete(target_date)

    def _uncomplete(self, target_date: date) -> None:
        """Uncomplete this daily for the target date"""
        self.streak_count = max(0, self.streak_count - 1)
        self.total_completions = max(0, self.total_completions - 1)

        # Set last completed to previous day if streak remains, else clear it
        if self.streak_count > 0:
            self.last_completed_date = target_date - timedelta(days=1)
        else:
            self.last_completed_date = None

    def _complete(self, target_date: date) -> None:
        """Complete this daily for the target date"""
        self.total_completions += 1
        self.streak_count = self._calculate_new_streak(target_date)
        self.last_completed_date = target_date

    # ---------- Streak calculation ----------

    def _calculate_new_streak(self, target_date: date) -> int:
        """
        Calculate the new streak count after completing on target_date.

        Returns:
            New streak count (either incremented or reset to 1)
        """
        if not self.last_completed_date:
            return 1

        days_since = (target_date - self.last_completed_date).days

        if self.frequency == "daily":
            return self._calculate_daily_streak(days_since)
        elif self.frequency == "weekly":
            return self._calculate_weekly_streak(days_since)
        elif self.frequency == "monthly":
            return self._calculate_monthly_streak(days_since)
        elif self.frequency == "custom":
            return self._calculate_custom_streak(days_since)

        return 1

    def _calculate_daily_streak(self, days_since: int) -> int:
        """Calculate streak for daily frequency"""
        if days_since == self.frequency_interval:
            return self.streak_count + 1
        return 1

    def _calculate_weekly_streak(self, days_since: int) -> int:
        """Calculate streak for weekly frequency"""
        week_interval = 7 * self.frequency_interval
        if week_interval <= days_since < (week_interval + 7):
            return self.streak_count + 1
        return 1

    def _calculate_monthly_streak(self, days_since: int) -> int:
        """Calculate streak for monthly frequency"""
        month_interval = 30 * self.frequency_interval
        if month_interval <= days_since < (month_interval + 30):
            return self.streak_count + 1
        return 1

    def _calculate_custom_streak(self, days_since: int) -> int:
        """Calculate streak for custom weekday frequency"""
        # For custom, streak works like daily within selected days
        if days_since == 1:
            return self.streak_count + 1
        return 1


class CompletionLog(db.Model):
    """Archive of completed todos/dailies for long-term tracking"""

    __tablename__ = "completion_logs"
    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "item_type",
            "item_id",
            "completed_date",
            name="uq_completion_per_day",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    item_type = db.Column(db.String(20), nullable=False)  # 'todo' or 'daily'
    item_id = db.Column(db.Integer, nullable=False)
    title_snapshot = db.Column(db.String(255), nullable=False)
    description_snapshot = db.Column(db.Text, nullable=True)
    completed_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return (
            f"<CompletionLog {self.item_type}#{self.item_id} on {self.completed_date}>"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "item_type": self.item_type,
            "item_id": self.item_id,
            "title": self.title_snapshot,
            "description": self.description_snapshot,
            "completed_date": self.completed_date.isoformat(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
