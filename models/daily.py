"""
Daily recurring task model and completion tracking
"""
import json
from datetime import date, datetime, timedelta

from extensions import db


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

    def should_complete_today(self) -> bool:
        """Check if this daily should be completable today based on frequency"""
        return self.should_complete_on(date.today())

    def should_complete_on(self, target_date: date) -> bool:
        """Check if this daily should be completable on a specific date"""
        weekday_names = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]
        target_weekday = weekday_names[target_date.weekday()]

        if (
            self.repeat_limit is not None
            and self.total_completions >= self.repeat_limit
        ):
            return False

        if self.last_completed_date and target_date < self.last_completed_date:
            return False

        if self.frequency == "daily":
            if not self.last_completed_date:
                return True
            days_since_last = (target_date - self.last_completed_date).days
            return days_since_last >= self.frequency_interval
        if self.frequency == "weekly":
            if not self.last_completed_date:
                return True
            days_since_last = (target_date - self.last_completed_date).days
            return days_since_last >= (7 * self.frequency_interval)
        if self.frequency == "monthly":
            if not self.last_completed_date:
                return True
            days_since_last = (target_date - self.last_completed_date).days
            return days_since_last >= (30 * self.frequency_interval)
        if self.frequency == "custom":
            return target_weekday in self.get_weekdays()

        return True

    def is_completed_on(self, target_date: date) -> bool:
        """Check if this daily was completed on a specific date"""
        if not self.last_completed_date:
            return False
        return self.last_completed_date == target_date

    def is_completed_today(self) -> bool:
        """Check if this daily was completed today"""
        return self.is_completed_on(date.today())

    def toggle_completion(self) -> None:
        """Toggle daily completion and update streak/totals"""
        today = date.today()

        if (
            self.repeat_limit is not None
            and self.total_completions >= self.repeat_limit
            and not self.is_completed_today()
        ):
            return

        if self.is_completed_today():
            # Uncomplete today's daily
            # Reduce streak and total
            self.streak_count = max(0, self.streak_count - 1)
            self.total_completions = max(0, self.total_completions - 1)
            # Set last completed to previous completion date if there was a streak, else None
            if self.streak_count > 0:
                self.last_completed_date = today - timedelta(days=1)
            else:
                self.last_completed_date = None
        else:
            # Complete today's daily
            self.total_completions += 1

            # Calculate streak based on frequency
            if self.frequency == "daily":
                if self.last_completed_date:
                    # Check if last completion was exactly (frequency_interval - 1) days ago
                    days_since = (today - self.last_completed_date).days
                    if days_since == self.frequency_interval:
                        self.streak_count += 1
                    else:
                        self.streak_count = 1
                else:
                    self.streak_count = 1
            elif self.frequency == "weekly":
                if self.last_completed_date:
                    days_since = (today - self.last_completed_date).days
                    week_interval = 7 * self.frequency_interval
                    if days_since >= week_interval and days_since < (week_interval + 7):
                        self.streak_count += 1
                    else:
                        self.streak_count = 1
                else:
                    self.streak_count = 1
            elif self.frequency == "monthly":
                if self.last_completed_date:
                    days_since = (today - self.last_completed_date).days
                    month_interval = 30 * self.frequency_interval
                    if days_since >= month_interval and days_since < (
                        month_interval + 30
                    ):
                        self.streak_count += 1
                    else:
                        self.streak_count = 1
                else:
                    self.streak_count = 1
            elif self.frequency == "custom":
                # For custom, streak works like daily within selected days
                if self.last_completed_date:
                    days_since = (today - self.last_completed_date).days
                    if days_since == 1:
                        self.streak_count += 1
                    else:
                        self.streak_count = 1
                else:
                    self.streak_count = 1

            self.last_completed_date = today

    def toggle_completion_on(self, target_date: date) -> None:
        """Toggle completion for a specific date (used for early scratch on Tomorrow)."""
        if not isinstance(target_date, date):
            return

        if (
            self.repeat_limit is not None
            and self.total_completions >= self.repeat_limit
            and not self.is_completed_on(target_date)
        ):
            return

        if self.is_completed_on(target_date):
            # Uncomplete for target date
            self.streak_count = max(0, self.streak_count - 1)
            self.total_completions = max(0, self.total_completions - 1)
            if self.streak_count > 0:
                self.last_completed_date = target_date - timedelta(days=1)
            else:
                self.last_completed_date = None
            return

        # Complete for target date
        self.total_completions += 1

        if self.frequency == "daily":
            # Streak logic analogous to toggle_completion but using target_date
            if self.last_completed_date:
                days_since = (target_date - self.last_completed_date).days
                if days_since == self.frequency_interval:
                    self.streak_count += 1
                else:
                    self.streak_count = 1
            else:
                self.streak_count = 1
        elif self.frequency == "weekly":
            if self.last_completed_date:
                days_since = (target_date - self.last_completed_date).days
                week_interval = 7 * self.frequency_interval
                if days_since >= week_interval and days_since < (week_interval + 7):
                    self.streak_count += 1
                else:
                    self.streak_count = 1
            else:
                self.streak_count = 1
        elif self.frequency == "monthly":
            if self.last_completed_date:
                days_since = (target_date - self.last_completed_date).days
                month_interval = 30 * self.frequency_interval
                if days_since >= month_interval and days_since < (month_interval + 30):
                    self.streak_count += 1
                else:
                    self.streak_count = 1
            else:
                self.streak_count = 1
        elif self.frequency == "custom":
            if self.last_completed_date:
                days_since = (target_date - self.last_completed_date).days
                if days_since == 1:
                    self.streak_count += 1
                else:
                    self.streak_count = 1
            else:
                self.streak_count = 1

        self.last_completed_date = target_date


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
