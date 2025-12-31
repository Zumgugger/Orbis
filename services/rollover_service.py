"""
Rollover service for handling daily task rollover and streak management
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from models.daily import Daily
    from models.todo import Todo
    from models.user import User


class RolloverService:
    """Service for processing daily rollover of todos and streak management."""

    def __init__(self, session: Any) -> None:
        """
        Initialize rollover service.

        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session

    def process_rollover(self, user: User) -> dict:
        """
        Process rollover for a user: shift unfinished items forward and break missed streaks.

        This method is idempotent - it tracks the last processed date to avoid
        double-shifting tasks when called multiple times on the same day.

        Args:
            user: User model instance with is_authenticated property

        Returns:
            Dict with info about missed dailies from yesterday
        """
        from models import RolloverState

        result = {"missed_yesterday": []}

        if not user.is_authenticated:
            return result

        today = date.today()
        yesterday = today - timedelta(days=1)
        state = RolloverState.query.filter_by(user_id=user.id).first()

        if not state:
            state = RolloverState(user_id=user.id, last_processed_date=today)
            self.session.add(state)
            self.session.commit()
            return result

        current_day = state.last_processed_date

        # Collect missed dailies from yesterday specifically (for the popup)
        if current_day <= yesterday:
            result["missed_yesterday"] = self._get_missed_dailies(user.id, yesterday)

        while current_day < today:
            next_day = current_day + timedelta(days=1)

            # Move pending todos forward by one day
            self._rollover_todos(user.id, current_day, next_day)

            # Break streak for dailies missed on the day (unless freeze is used)
            # Skip yesterday - we'll let user mark them complete first
            if current_day < yesterday:
                self._break_missed_streaks(user.id, current_day)

            self.session.commit()
            current_day = next_day

        state.last_processed_date = today
        self.session.commit()

        return result

    def _get_missed_dailies(self, user_id: int, check_date: date) -> list[Daily]:
        """
        Get dailies that were due but not completed on a given date.

        Args:
            user_id: ID of the user
            check_date: Date to check for missed completions

        Returns:
            List of Daily instances that were missed
        """
        from models import Daily

        user_dailies = Daily.query.filter_by(user_id=user_id).all()
        missed: list[Daily] = []

        for daily in user_dailies:
            if daily.should_complete_on(check_date) and not daily.is_completed_on(
                check_date
            ):
                missed.append(daily)

        return missed

    def _rollover_todos(
        self, user_id: int, from_date: date, to_date: date
    ) -> list[Todo]:
        """
        Roll over pending todos from one date to the next.

        Args:
            user_id: ID of the user
            from_date: Source date for pending todos
            to_date: Target date to move todos to

        Returns:
            List of rolled over Todo instances
        """
        from models import Todo

        pending_todos = Todo.query.filter(
            Todo.user_id == user_id,
            Todo.status == "pending",
            Todo.due_date == from_date,
        ).all()

        for todo in pending_todos:
            todo.due_date = to_date

        return pending_todos

    def _break_missed_streaks(self, user_id: int, check_date: date) -> list[Daily]:
        """
        Break streaks for dailies that were due but not completed on a given date.

        Args:
            user_id: ID of the user
            check_date: Date to check for missed completions

        Returns:
            List of Daily instances with broken streaks
        """
        from models import Daily

        user_dailies = Daily.query.filter_by(user_id=user_id).all()
        broken_streaks: list[Daily] = []

        for daily in user_dailies:
            if daily.should_complete_on(check_date) and not daily.is_completed_on(
                check_date
            ):
                daily.streak_count = 0
                broken_streaks.append(daily)

        return broken_streaks

    def get_rollover_status(self, user: User) -> dict:
        """
        Get rollover status information for a user.

        Args:
            user: User model instance

        Returns:
            Dict with rollover status info
        """
        from models import RolloverState

        state = RolloverState.query.filter_by(user_id=user.id).first()

        if not state:
            return {
                "has_state": False,
                "last_processed_date": None,
                "days_behind": 0,
            }

        today = date.today()
        days_behind = (today - state.last_processed_date).days

        return {
            "has_state": True,
            "last_processed_date": state.last_processed_date.isoformat(),
            "days_behind": days_behind,
        }
