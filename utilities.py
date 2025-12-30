"""
Shared utility functions for blueprints
Provides common helpers for time labels, combined lists, redirects, etc.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING, Any, TypedDict

from flask import current_app, jsonify, render_template, request, url_for

if TYPE_CHECKING:
    from werkzeug import Response

    from models.daily import Daily
    from models.todo import Todo


class CalendarEvent(TypedDict, total=False):
    """Type definition for calendar event dict"""

    title: str
    start_raw: str | None
    end_raw: str | None
    start_dt: Any | None
    end_dt: Any | None
    all_day: bool
    html_link: str | None
    time_label: str


class CombinedItem(TypedDict):
    """Type definition for combined todo/calendar item"""

    kind: str
    event: CalendarEvent | None
    todo: Todo | None


class PriorityDisplay(TypedDict):
    """Type definition for priority display info"""

    name: str
    badge_class: str
    icon: str


class DifficultyDisplay(TypedDict):
    """Type definition for difficulty display info"""

    name: str
    badge_class: str


def get_next_url(default_endpoint: str = "index", **kwargs: Any) -> str:
    """
    Get the next redirect URL from request args or use default

    Args:
        default_endpoint: Default Flask endpoint if no 'next' param
        **kwargs: Additional arguments for url_for()

    Returns:
        URL to redirect to
    """
    next_url = request.args.get("next")

    # Validate next URL is relative (security: prevent open redirects)
    if next_url and next_url.startswith("/"):
        return next_url

    return url_for(default_endpoint, **kwargs)


def build_redirect_with_next(
    endpoint: str, next_endpoint: str | None = None, **url_params: Any
) -> str:
    """
    Build a URL with a 'next' parameter for return navigation

    Args:
        endpoint: Flask endpoint to build URL for
        next_endpoint: Optional endpoint to set as 'next' parameter
        **url_params: Additional URL parameters

    Returns:
        URL with next parameter
    """
    base_url = url_for(endpoint, **url_params)

    if next_endpoint:
        next_url = url_for(next_endpoint)
        return f"{base_url}?next={next_url}"

    return base_url


def generate_time_label(
    event_datetime: Any | None, date_label: str = "Today", include_time: bool = True
) -> str:
    """
    Generate a time label for calendar events

    Args:
        event_datetime: datetime object or None
        date_label: Label for the date (e.g., 'Today', 'Tomorrow')
        include_time: Whether to include time in label

    Returns:
        Formatted time label
    """
    if not event_datetime:
        return date_label

    if not include_time:
        return f"{date_label} · All-day"

    return f"{date_label} · {event_datetime.strftime('%H:%M')}"


def combine_todos_and_calendar(
    todos: list[Todo], calendar_events: list[CalendarEvent], date_label: str = "Today"
) -> list[dict[str, Any]]:
    """
    Combine todos and calendar events into a single list with time labels

    Args:
        todos: List of Todo objects
        calendar_events: List of calendar event dicts
        date_label: Label for the date (e.g., 'Today', 'Tomorrow')

    Returns:
        Combined list with 'kind' and object keys
    """
    # Add time labels to calendar events
    for event in calendar_events:
        if event.get("all_day"):
            event["time_label"] = generate_time_label(
                None, date_label, include_time=False
            )
        else:
            event["time_label"] = generate_time_label(
                event.get("start_dt"), date_label, include_time=True
            )

    # Build combined list
    combined: list[dict[str, Any]] = [
        {"kind": "calendar", "event": ev} for ev in calendar_events
    ]
    combined += [{"kind": "todo", "todo": t} for t in todos]

    return combined


def filter_dailies_for_date(
    all_dailies: list[Daily],
    target_date: date,
    include_carryover: bool = False,
    carryover_date: date | None = None,
) -> tuple[list[Daily], set[int]] | list[Daily]:
    """
    Filter dailies that should appear on a specific date

    Args:
        all_dailies: List of all Daily objects
        target_date: date object to filter for
        include_carryover: Whether to include uncompleted items from previous day
        carryover_date: date to check for carryover (defaults to target_date - 1)

    Returns:
        (filtered_dailies, carryover_ids) if include_carryover else filtered_dailies
    """
    if include_carryover and carryover_date is None:
        carryover_date = target_date - timedelta(days=1)

    carryover_ids: set[int] = set()
    due_ids: set[int] = set()

    for daily in all_dailies:
        # Check carryover from previous day
        if include_carryover and carryover_date:
            if daily.should_complete_on(carryover_date) and not daily.is_completed_on(
                carryover_date
            ):
                carryover_ids.add(daily.id)

        # Check if due on target date
        if daily.should_complete_on(target_date):
            due_ids.add(daily.id)

    filtered = [
        daily
        for daily in all_dailies
        if daily.id in due_ids or (include_carryover and daily.id in carryover_ids)
    ]

    if include_carryover:
        return filtered, carryover_ids

    return filtered


def format_filesize(size_bytes: int | float) -> str:
    """
    Format file size in human-readable format

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size (e.g., "1.5 MB", "342 KB")
    """
    size = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def format_duration(hours: int = 0, minutes: int = 0) -> str:
    """
    Format duration as human-readable string

    Args:
        hours: Number of hours
        minutes: Number of minutes

    Returns:
        Formatted duration
    """
    parts: list[str] = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    return " ".join(parts) if parts else "0m"


def get_frequency_display_name(frequency_code: str) -> str:
    """
    Get display name for frequency code

    Args:
        frequency_code: String frequency code (e.g., 'daily', 'weekly', 'custom')

    Returns:
        Human-readable frequency name
    """
    frequency_map = {
        "daily": "Every day",
        "weekly": "Weekly",
        "custom": "Custom schedule",
        "weekdays": "Weekdays only",
        "weekends": "Weekends only",
    }
    return frequency_map.get(frequency_code, frequency_code.capitalize())


def get_priority_display(priority_code: str) -> PriorityDisplay:
    """
    Get display information for priority level

    Args:
        priority_code: String priority code (e.g., 'low', 'medium', 'high')

    Returns:
        Dict with name, badge_class, and icon
    """
    priority_map: dict[str, PriorityDisplay] = {
        "low": {
            "name": "Low",
            "badge_class": "badge-secondary",
            "icon": "bi-arrow-down-circle",
        },
        "medium": {
            "name": "Medium",
            "badge_class": "badge-warning",
            "icon": "bi-circle-fill",
        },
        "high": {
            "name": "High",
            "badge_class": "badge-danger",
            "icon": "bi-exclamation-triangle-fill",
        },
    }
    return priority_map.get(
        priority_code,
        {
            "name": priority_code.capitalize(),
            "badge_class": "badge-secondary",
            "icon": "bi-circle",
        },
    )


def get_difficulty_display(difficulty_code: str) -> DifficultyDisplay:
    """
    Get display information for difficulty level

    Args:
        difficulty_code: String difficulty code (e.g., 'trivial', 'easy', 'medium', 'hard')

    Returns:
        Dict with name and badge_class
    """
    difficulty_map: dict[str, DifficultyDisplay] = {
        "trivial": {"name": "Trivial", "badge_class": "badge-secondary"},
        "easy": {"name": "Easy", "badge_class": "badge-success"},
        "medium": {"name": "Medium", "badge_class": "badge-warning"},
        "hard": {"name": "Hard", "badge_class": "badge-danger"},
    }
    return difficulty_map.get(
        difficulty_code,
        {"name": difficulty_code.capitalize(), "badge_class": "badge-secondary"},
    )


def is_overdue(due_date: date | None, current_date: date | None = None) -> bool:
    """
    Check if a due date is in the past

    Args:
        due_date: date object
        current_date: date object (defaults to today)

    Returns:
        True if overdue
    """
    if not due_date:
        return False

    if current_date is None:
        from time_utils import today_local

        current_date = today_local()

    return due_date < current_date


def group_by_status(
    items: list[Any], status_attr: str = "status"
) -> dict[str, list[Any]]:
    """
    Group items by their status attribute

    Args:
        items: List of objects with status attribute
        status_attr: Name of the status attribute (default: 'status')

    Returns:
        Dict mapping status to list of items
    """
    groups: dict[str, list[Any]] = {}
    for item in items:
        status = getattr(item, status_attr, "unknown")
        if status not in groups:
            groups[status] = []
        groups[status].append(item)
    return groups


# Error/response helpers
def error_message(exc: Exception, default_msg: str) -> str:
    """Pick a human-readable message from the exception."""
    return getattr(exc, "description", None) or str(exc) or default_msg


def wants_json_response() -> bool:
    """Return True when the client prefers JSON over HTML."""
    accepts = request.accept_mimetypes
    return (
        request.path.startswith("/api/")
        or request.is_json
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or accepts.best == "application/json"
        or accepts["application/json"] > accepts["text/html"]
    )


def error_response(
    status_code: int, error_key: str, message: str, template: str
) -> tuple[Response, int] | tuple[str, int]:
    """Generate error response in JSON or HTML format based on client preference."""
    payload = {
        "status": status_code,
        "error": error_key,
        "message": message,
        "path": request.path,
    }
    if wants_json_response():
        return jsonify(payload), status_code
    return render_template(template), status_code


# Structured logging helpers
def _with_context(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build context dict for structured logging."""
    ctx: dict[str, Any] = {
        "path": request.path if request else None,
        "method": request.method if request else None,
        "remote_addr": request.remote_addr if request else None,
    }
    try:
        from flask_login import current_user

        ctx["user_id"] = getattr(current_user, "id", None)
    except Exception:
        ctx["user_id"] = None
    if extra and isinstance(extra, dict):
        ctx.update(extra)
    return ctx


def log_warning(message: str, extra: dict[str, Any] | None = None) -> None:
    """Log a warning with request context."""
    logger = getattr(current_app, "logger", None)
    if logger:
        logger.warning({"message": message, **_with_context(extra)})


def log_error(message: str, extra: dict[str, Any] | None = None) -> None:
    """Log an error with request context."""
    logger = getattr(current_app, "logger", None)
    if logger:
        logger.error({"message": message, **_with_context(extra)})


def log_exception(
    exc: Exception, message: str | None = None, extra: dict[str, Any] | None = None
) -> None:
    """Log an exception with full traceback and request context."""
    logger = getattr(current_app, "logger", None)
    if logger:
        logger.exception(
            {
                "message": message or str(exc),
                "exception": str(exc),
                **_with_context(extra),
            }
        )


def build_json_error(
    error_key: str,
    message: str,
    status: int = 400,
    extra: dict[str, Any] | None = None,
) -> tuple[Response, int]:
    """
    Build a consistent JSON error payload and log appropriately.
    """
    payload: dict[str, Any] = {
        "status": status,
        "error": error_key,
        "message": message,
        "path": request.path,
    }
    if extra and isinstance(extra, dict):
        payload["extra"] = extra
    if status >= 500:
        log_exception(Exception(message), message=message, extra=extra)
    else:
        log_warning(message, extra=extra)
    return jsonify(payload), status
