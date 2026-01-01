"""
Calendar service for Google Calendar integration
"""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta
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
        calendar_id: str = "primary",
    ) -> list[dict[str, Any]]:
        """
        Fetch calendar events from Google Calendar API.

        Args:
            oauth_client: OAuth client for API calls
            token: OAuth token dict for authentication
            start_date: Start date (inclusive)
            end_date: End date (exclusive)
            calendar_id: Calendar ID to fetch from (default: primary)

        Returns:
            List of event dictionaries
        """
        time_min = iso_start_of_day(start_date)
        time_max = iso_start_of_day(end_date)

        try:
            resp = oauth_client.get(
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
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
                    "id": item.get("id"),
                    "title": item.get("summary") or "(No title)",
                    "description": item.get("description", ""),
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

    # ==================== Write Operations ====================

    def create_event(
        self,
        oauth_client: Any,
        token: dict[str, Any],
        title: str,
        description: str | None = None,
        event_date: date | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        duration_minutes: int = 60,
        calendar_id: str = "primary",
    ) -> dict[str, Any] | None:
        """
        Create a new calendar event.

        Args:
            oauth_client: OAuth client for API calls
            token: OAuth token dict for authentication
            title: Event title/summary
            description: Event description (optional)
            event_date: Date for all-day event (if no start_time)
            start_time: Start datetime (timezone-aware)
            end_time: End datetime (timezone-aware, optional)
            duration_minutes: Duration in minutes if no end_time
            calendar_id: Calendar ID to create event in (default: primary)

        Returns:
            Created event dict with 'id' and 'htmlLink', or None on failure
        """
        tz = os.getenv("DEFAULT_TIMEZONE", "Europe/Zurich")

        event: dict[str, Any] = {
            "summary": title,
            "description": description or "",
        }

        if start_time:
            # Timed event
            if not end_time:
                end_time = start_time + timedelta(minutes=duration_minutes)
            event["start"] = {"dateTime": start_time.isoformat(), "timeZone": tz}
            event["end"] = {"dateTime": end_time.isoformat(), "timeZone": tz}
        elif event_date:
            # All-day event
            event["start"] = {"date": event_date.isoformat()}
            event["end"] = {"date": (event_date + timedelta(days=1)).isoformat()}
        else:
            if self.logger:
                self.logger.error("create_event: No date or time provided")
            return None

        try:
            resp = oauth_client.post(
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
                json=event,
                token=token,
            )

            if resp.status_code in (200, 201):
                data = resp.json()
                if self.logger:
                    self.logger.info(f"Created calendar event: {data.get('id')}")
                return {
                    "id": data.get("id"),
                    "htmlLink": data.get("htmlLink"),
                }
            else:
                if self.logger:
                    self.logger.error(
                        f"Failed to create event: {resp.status_code} - {resp.text}"
                    )
                # Return error dict for token issues so caller can redirect to re-auth
                if resp.status_code in (401, 403):
                    return {"error": "token_invalid"}
                return None
        except Exception as exc:
            if self.logger:
                self.logger.exception(f"Exception creating calendar event: {exc}")
            # Check if it's an auth-related exception
            exc_str = str(exc).lower()
            if (
                "token" in exc_str
                or "auth" in exc_str
                or "401" in exc_str
                or "403" in exc_str
            ):
                return {"error": "token_invalid"}
            return None

    def update_event(
        self,
        oauth_client: Any,
        token: dict[str, Any],
        event_id: str,
        title: str | None = None,
        description: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        event_date: date | None = None,
        mark_completed: bool = False,
        calendar_id: str = "primary",
    ) -> bool:
        """
        Update an existing calendar event.

        Args:
            oauth_client: OAuth client for API calls
            token: OAuth token dict for authentication
            event_id: Google Calendar event ID
            title: New title (optional)
            description: New description (optional)
            start_time: New start datetime (optional)
            end_time: New end datetime (optional)
            event_date: New date for all-day event (optional)
            mark_completed: If True, prefix title with checkmark
            calendar_id: Calendar ID where event exists (default: primary)

        Returns:
            True if successful, False otherwise
        """
        tz = os.getenv("DEFAULT_TIMEZONE", "Europe/Zurich")

        # First, get the current event
        try:
            get_resp = oauth_client.get(
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}",
                token=token,
            )
            if get_resp.status_code != 200:
                if self.logger:
                    self.logger.warning(
                        f"Failed to get event {event_id}: {get_resp.status_code}"
                    )
                # Return error string for token issues so caller can redirect to re-auth
                if get_resp.status_code in (401, 403):
                    return "token_invalid"
                return False

            current_event = get_resp.json()
        except Exception as exc:
            if self.logger:
                self.logger.exception(f"Exception getting event {event_id}: {exc}")
            return False

        # Build update payload
        update_data: dict[str, Any] = {}

        if title is not None:
            update_data["summary"] = title
        if description is not None:
            update_data["description"] = description
        if mark_completed:
            current_title = current_event.get("summary", "")
            if not current_title.startswith("\u2713"):
                update_data["summary"] = f"\u2713 {current_title}"

        if start_time and end_time:
            update_data["start"] = {"dateTime": start_time.isoformat(), "timeZone": tz}
            update_data["end"] = {"dateTime": end_time.isoformat(), "timeZone": tz}
        elif event_date:
            update_data["start"] = {"date": event_date.isoformat()}
            update_data["end"] = {"date": (event_date + timedelta(days=1)).isoformat()}

        if not update_data:
            return True  # Nothing to update

        try:
            resp = oauth_client.patch(
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}",
                json=update_data,
                token=token,
            )

            if resp.status_code == 200:
                if self.logger:
                    self.logger.info(f"Updated calendar event: {event_id}")
                return True
            else:
                if self.logger:
                    self.logger.error(
                        f"Failed to update event {event_id}: {resp.status_code}"
                    )
                # Return error string for token issues so caller can redirect to re-auth
                if resp.status_code in (401, 403):
                    return "token_invalid"
                return False
        except Exception as exc:
            if self.logger:
                self.logger.exception(f"Exception updating event {event_id}: {exc}")
            return False

    def delete_event(
        self,
        oauth_client: Any,
        token: dict[str, Any],
        event_id: str,
        calendar_id: str = "primary",
    ) -> bool:
        """
        Delete a calendar event.

        Args:
            oauth_client: OAuth client for API calls
            token: OAuth token dict for authentication
            event_id: Google Calendar event ID
            calendar_id: Calendar ID where event exists (default: primary)

        Returns:
            True if successful, False otherwise
        """
        try:
            resp = oauth_client.delete(
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}",
                token=token,
            )

            # 204 No Content = success, 410 Gone = already deleted
            if resp.status_code in (204, 410):
                if self.logger:
                    self.logger.info(f"Deleted calendar event: {event_id}")
                return True
            else:
                if self.logger:
                    self.logger.error(
                        f"Failed to delete event {event_id}: {resp.status_code}"
                    )
                # Return error string for token issues so caller can redirect to re-auth
                if resp.status_code in (401, 403):
                    return "token_invalid"
                return False
        except Exception as exc:
            if self.logger:
                self.logger.exception(f"Exception deleting event {event_id}: {exc}")
            return False

    def get_event(
        self,
        oauth_client: Any,
        token: dict[str, Any],
        event_id: str,
        calendar_id: str = "primary",
    ) -> dict[str, Any] | None:
        """
        Get a calendar event by ID.

        Args:
            oauth_client: OAuth client for API calls
            token: OAuth token dict for authentication
            event_id: Google Calendar event ID
            calendar_id: Calendar ID where event exists (default: primary)

        Returns:
            Event data dict if successful, None otherwise
        """
        try:
            resp = oauth_client.get(
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}",
                token=token,
            )

            if resp.status_code == 200:
                return resp.json()
            else:
                if self.logger:
                    self.logger.warning(
                        f"Failed to get event {event_id}: {resp.status_code}"
                    )
                return None
        except Exception as exc:
            if self.logger:
                self.logger.exception(f"Exception getting event {event_id}: {exc}")
            return None

    def unmark_completed(
        self,
        oauth_client: Any,
        token: dict[str, Any],
        event_id: str,
        calendar_id: str = "primary",
    ) -> bool:
        """
        Remove the completion mark from an event title.

        Args:
            oauth_client: OAuth client for API calls
            token: OAuth token dict for authentication
            event_id: Google Calendar event ID
            calendar_id: Calendar ID where event exists (default: primary)

        Returns:
            True if successful, False otherwise
        """
        try:
            get_resp = oauth_client.get(
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}",
                token=token,
            )
            if get_resp.status_code != 200:
                return False

            current_event = get_resp.json()
            current_title = current_event.get("summary", "")

            # Remove completion mark if present
            if current_title.startswith("\u2713 "):
                new_title = current_title[2:]
            elif current_title.startswith("\u2713"):
                new_title = current_title[1:]
            else:
                return True  # No mark to remove

            resp = oauth_client.patch(
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}",
                json={"summary": new_title},
                token=token,
            )

            return resp.status_code == 200
        except Exception as exc:
            if self.logger:
                self.logger.exception(f"Exception unmarking event {event_id}: {exc}")
            return False

    def create_multiday_event(
        self,
        oauth_client: Any,
        token: dict[str, Any],
        title: str,
        start_date: date,
        end_date: date,
        description: str | None = None,
        calendar_id: str = "primary",
    ) -> dict[str, Any] | None:
        """
        Create a multi-day all-day event (e.g., vacations, holidays).

        Args:
            oauth_client: OAuth client for API calls
            token: OAuth token dict for authentication
            title: Event title/summary
            start_date: First day of the event (inclusive)
            end_date: Last day of the event (inclusive)
            description: Event description (optional)
            calendar_id: Calendar ID to create event in (default: primary)

        Returns:
            Created event dict with 'id' and 'htmlLink', or None on failure
        """
        # Google Calendar API expects end date to be exclusive (day after last day)
        end_date_exclusive = end_date + timedelta(days=1)

        event: dict[str, Any] = {
            "summary": title,
            "description": description or "",
            "start": {"date": start_date.isoformat()},
            "end": {"date": end_date_exclusive.isoformat()},
        }

        try:
            resp = oauth_client.post(
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
                json=event,
                token=token,
            )

            if resp.status_code in (200, 201):
                data = resp.json()
                if self.logger:
                    self.logger.info(f"Created multi-day event: {data.get('id')}")
                return {
                    "id": data.get("id"),
                    "htmlLink": data.get("htmlLink"),
                }
            else:
                if self.logger:
                    self.logger.error(
                        f"Failed to create multi-day event: {resp.status_code} - {resp.text}"
                    )
                if resp.status_code in (401, 403):
                    return {"error": "token_invalid"}
                return None
        except Exception as exc:
            if self.logger:
                self.logger.exception(f"Exception creating multi-day event: {exc}")
            return None
