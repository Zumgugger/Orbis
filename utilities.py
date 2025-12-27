"""
Shared utility functions for blueprints
Provides common helpers for time labels, combined lists, redirects, etc.
"""
from datetime import timedelta

from flask import current_app, jsonify, render_template, request, url_for


def get_next_url(default_endpoint="index", **kwargs):
    """
    Get the next redirect URL from request args or use default

    Args:
        default_endpoint: Default Flask endpoint if no 'next' param
        **kwargs: Additional arguments for url_for()

    Returns:
        str: URL to redirect to

    Example:
        return redirect(get_next_url('todos.list_todos'))
        return redirect(get_next_url('index', _anchor='todos'))
    """
    next_url = request.args.get("next")

    # Validate next URL is relative (security: prevent open redirects)
    if next_url and next_url.startswith("/"):
        return next_url

    return url_for(default_endpoint, **kwargs)


def build_redirect_with_next(endpoint, next_endpoint=None, **url_params):
    """
    Build a URL with a 'next' parameter for return navigation

    Args:
        endpoint: Flask endpoint to build URL for
        next_endpoint: Optional endpoint to set as 'next' parameter
        **url_params: Additional URL parameters

    Returns:
        str: URL with next parameter

    Example:
        url = build_redirect_with_next('todos.edit_todo',
                                       next_endpoint='index',
                                       todo_id=5)
        # Returns: /todos/5/edit?next=/
    """
    base_url = url_for(endpoint, **url_params)

    if next_endpoint:
        next_url = url_for(next_endpoint)
        return f"{base_url}?next={next_url}"

    return base_url


def generate_time_label(event_datetime, date_label="Today", include_time=True):
    """
    Generate a time label for calendar events

    Args:
        event_datetime: datetime object or None
        date_label: Label for the date (e.g., 'Today', 'Tomorrow')
        include_time: Whether to include time in label

    Returns:
        str: Formatted time label

    Example:
        generate_time_label(datetime(2025, 12, 27, 14, 30), 'Today')
        # Returns: "Today · 14:30"

        generate_time_label(None, 'Tomorrow')
        # Returns: "Tomorrow"
    """
    if not event_datetime:
        return date_label

    if not include_time:
        return f"{date_label} · All-day"

    return f"{date_label} · {event_datetime.strftime('%H:%M')}"


def combine_todos_and_calendar(todos, calendar_events, date_label="Today"):
    """
    Combine todos and calendar events into a single list with time labels

    Args:
        todos: List of Todo objects
        calendar_events: List of calendar event dicts
        date_label: Label for the date (e.g., 'Today', 'Tomorrow')

    Returns:
        list: Combined list with 'kind' and object keys

    Example:
        combined = combine_todos_and_calendar(todos_today, events, 'Today')
        # Returns: [
        #   {'kind': 'calendar', 'event': {..., 'time_label': 'Today · 14:00'}},
        #   {'kind': 'todo', 'todo': <Todo object>}
        # ]
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
    combined = [{"kind": "calendar", "event": ev} for ev in calendar_events]
    combined += [{"kind": "todo", "todo": t} for t in todos]

    return combined


def filter_dailies_for_date(
    all_dailies, target_date, include_carryover=False, carryover_date=None
):
    """
    Filter dailies that should appear on a specific date

    Args:
        all_dailies: List of all Daily objects
        target_date: date object to filter for
        include_carryover: Whether to include uncompleted items from previous day
        carryover_date: date to check for carryover (defaults to target_date - 1)

    Returns:
        tuple: (filtered_dailies, carryover_ids) if include_carryover else filtered_dailies

    Example:
        dailies_tomorrow = filter_dailies_for_date(all_dailies, tomorrow_date)

        dailies_tomorrow, carryover = filter_dailies_for_date(
            all_dailies, tomorrow_date, include_carryover=True, carryover_date=today
        )
    """
    if include_carryover and carryover_date is None:
        carryover_date = target_date - timedelta(days=1)

    carryover_ids = set()
    due_ids = set()

    for daily in all_dailies:
        # Check carryover from previous day
        if include_carryover:
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


def format_filesize(size_bytes):
    """
    Format file size in human-readable format

    Args:
        size_bytes: Size in bytes (int)

    Returns:
        str: Formatted size (e.g., "1.5 MB", "342 KB")

    Example:
        format_filesize(1536000)  # Returns: "1.5 MB"
        format_filesize(2048)      # Returns: "2.0 KB"
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def format_duration(hours=0, minutes=0):
    """
    Format duration as human-readable string

    Args:
        hours: Number of hours
        minutes: Number of minutes

    Returns:
        str: Formatted duration

    Example:
        format_duration(2, 30)  # Returns: "2h 30m"
        format_duration(0, 45)   # Returns: "45m"
        format_duration(1, 0)    # Returns: "1h"
    """
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    return " ".join(parts) if parts else "0m"


def get_frequency_display_name(frequency_code):
    """
    Get display name for frequency code

    Args:
        frequency_code: String frequency code (e.g., 'daily', 'weekly', 'custom')

    Returns:
        str: Human-readable frequency name

    Example:
        get_frequency_display_name('daily')    # Returns: "Every day"
        get_frequency_display_name('weekly')   # Returns: "Weekly"
        get_frequency_display_name('custom')   # Returns: "Custom schedule"
    """
    frequency_map = {
        "daily": "Every day",
        "weekly": "Weekly",
        "custom": "Custom schedule",
        "weekdays": "Weekdays only",
        "weekends": "Weekends only",
    }
    return frequency_map.get(frequency_code, frequency_code.capitalize())


def get_priority_display(priority_code):
    """
    Get display information for priority level

    Args:
        priority_code: String priority code (e.g., 'low', 'medium', 'high')

    Returns:
        dict: {'name': str, 'badge_class': str, 'icon': str}

    Example:
        get_priority_display('high')
        # Returns: {
        #   'name': 'High',
        #   'badge_class': 'badge-danger',
        #   'icon': 'bi-exclamation-triangle-fill'
        # }
    """
    priority_map = {
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


def get_difficulty_display(difficulty_code):
    """
    Get display information for difficulty level

    Args:
        difficulty_code: String difficulty code (e.g., 'trivial', 'easy', 'medium', 'hard')

    Returns:
        dict: {'name': str, 'badge_class': str}

    Example:
        get_difficulty_display('hard')
        # Returns: {'name': 'Hard', 'badge_class': 'badge-danger'}
    """
    difficulty_map = {
        "trivial": {"name": "Trivial", "badge_class": "badge-secondary"},
        "easy": {"name": "Easy", "badge_class": "badge-success"},
        "medium": {"name": "Medium", "badge_class": "badge-warning"},
        "hard": {"name": "Hard", "badge_class": "badge-danger"},
    }
    return difficulty_map.get(
        difficulty_code,
        {"name": difficulty_code.capitalize(), "badge_class": "badge-secondary"},
    )


def is_overdue(due_date, current_date=None):
    """
    Check if a due date is in the past

    Args:
        due_date: date object
        current_date: date object (defaults to today)

    Returns:
        bool: True if overdue

    Example:
        is_overdue(date(2025, 12, 20))  # Returns: True (if today is later)
    """
    if not due_date:
        return False

    if current_date is None:
        from time_utils import today_local

        current_date = today_local()

    return due_date < current_date


def group_by_status(items, status_attr="status"):
    """
    Group items by their status attribute

    Args:
        items: List of objects with status attribute
        status_attr: Name of the status attribute (default: 'status')

    Returns:
        dict: {status: [items]}

    Example:
        groups = group_by_status(todos)
        # Returns: {'pending': [...], 'completed': [...]}
    """
    groups = {}
    for item in items:
        status = getattr(item, status_attr, "unknown")
        if status not in groups:
            groups[status] = []
        groups[status].append(item)
    return groups


# Error/response helpers
def error_message(exc, default_msg):
    """Pick a human-readable message from the exception."""
    return getattr(exc, "description", None) or str(exc) or default_msg


def wants_json_response():
    """Return True when the client prefers JSON over HTML."""
    accepts = request.accept_mimetypes
    return (
        request.path.startswith("/api/")
        or request.is_json
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or accepts.best == "application/json"
        or accepts["application/json"] > accepts["text/html"]
    )


def error_response(status_code, error_key, message, template):
    payload = {
        "status": status_code,
        "error": error_key,
        "message": message,
        "path": request.path,
    }
    if wants_json_response():
        return jsonify(payload), status_code
    return render_template(template), status_code


# Structured logging helpers and JSON error builder
def _with_context(extra=None):
    ctx = {
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


def log_warning(message, extra=None):
    logger = getattr(current_app, "logger", None)
    if logger:
        logger.warning({"message": message, **_with_context(extra)})


def log_error(message, extra=None):
    logger = getattr(current_app, "logger", None)
    if logger:
        logger.error({"message": message, **_with_context(extra)})


def log_exception(exc, message=None, extra=None):
    logger = getattr(current_app, "logger", None)
    if logger:
        logger.exception(
            {
                "message": message or str(exc),
                "exception": str(exc),
                **_with_context(extra),
            }
        )


def build_json_error(error_key, message, status=400, extra=None):
    """
    Build a consistent JSON error payload and log appropriately.

    Note: This does not enforce usage across all endpoints to avoid breaking tests.
    """
    payload = {
        "status": status,
        "error": error_key,
        "message": message,
        "path": request.path,
    }
    if extra and isinstance(extra, dict):
        payload.update({"extra": extra})
    if status >= 500:
        log_exception(Exception(message), message=message, extra=extra)
    else:
        log_warning(message, extra=extra)
    return jsonify(payload), status
