"""
Calendar service for Google Calendar integration
"""
from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from logging import Logger

    from zoneinfo import ZoneInfo

from time_utils import get_local_tz, iso_start_of_day


class CalendarService:
    """Service for fetching and processing calendar events."""

    def __init__(self, logger: Logger | None = None) -> None:
        """
        Initialize calendar service.

        Args:
            logger: Optional logger instance
        """
        self.logger = logger
        self._tz: ZoneInfo | None = None

    @property
    def timezone(self) -> ZoneInfo:
        """Get the local timezone."""
        if self._tz is None:
            self._tz = get_local_tz()
        return self._tz

    def fetch_events_for_user(
        self,
        user: Any,
        start_date: date,
        end_date: date,
        get_token_func: Any,
        oauth_client: Any,
    ) -> list[dict[str, Any]]:
        """
        Fetch calendar events for a user.

        Args:
            user: User object
            start_date: Start date (inclusive)
            end_date: End date (exclusive)
            get_token_func: Function to get OAuth token for user
            oauth_client: OAuth client for API calls

        Returns:
            List of event dictionaries
        """
        token = get_token_func(user, logger=self.logger)
        if not token:
            return []

        return self._fetch_events(oauth_client, token, start_date, end_date)

    def _fetch_events(
        self,
        oauth_client: Any,
        token: dict[str, Any],
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """
        Fetch calendar events from Google Calendar API.

        Args:
            oauth_client: OAuth client for API calls
            token: OAuth token dict for authentication
            start_date: Start date (inclusive)
            end_date: End date (exclusive)

        Returns:
            List of event dictionaries
        """
        time_min = iso_start_of_day(start_date)
        time_max = iso_start_of_day(end_date)

        try:
            resp = oauth_client.get(
                "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                params={
                    "timeMin": time_min,
                    "timeMax": time_max,
                    "singleEvents": True,
                    "orderBy": "startTime",
                },
                token=token,
            )
        except Exception as exc:
            if self.logger:
                self.logger.warning(f"Calendar fetch failed: {exc}")
            return []

        if resp.status_code != 200:
            if self.logger:
                self.logger.warning(
                    f"Calendar fetch returned {resp.status_code}: {resp.text}"
                )
            return []

        return self._parse_events(resp.json())

    def _parse_events(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Parse raw calendar API response into event list.

        Args:
            data: Raw API response JSON

        Returns:
            List of parsed event dictionaries
        """
        events: list[dict[str, Any]] = []

        for item in data.get("items", []):
            start = item.get("start", {})
            end = item.get("end", {})
            is_all_day = "date" in start
            raw_start = start.get("dateTime") or start.get("date")
            raw_end = end.get("dateTime") or end.get("date")

            start_dt = self._parse_datetime(raw_start) if not is_all_day else None
            end_dt = self._parse_datetime(raw_end) if not is_all_day else None

            events.append(
                {
                    "title": item.get("summary") or "(No title)",
                    "start_raw": raw_start,
                    "end_raw": raw_end,
                    "start_dt": start_dt,
                    "end_dt": end_dt,
                    "all_day": is_all_day,
                    "html_link": item.get("htmlLink"),
                }
            )

        return events

    def _parse_datetime(self, val: str | None) -> datetime | None:
        """
        Parse ISO datetime string to timezone-aware datetime.

        Args:
            val: ISO datetime string

        Returns:
            Parsed datetime or None
        """
        if not val:
            return None
        try:
            dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
            return dt.astimezone(self.timezone)
        except Exception:
            return None
