"""
Time and timezone utilities
Provides consistent handling of local time throughout the application
"""
from __future__ import annotations

import os
from datetime import date, datetime, time, timedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore[import-not-found,no-redef]

_DEFAULT_TZ_NAME: str = os.getenv("DEFAULT_TIMEZONE", "Europe/Zurich")


def get_local_tz() -> ZoneInfo:
    """Get the configured local timezone."""
    try:
        return ZoneInfo(_DEFAULT_TZ_NAME)
    except Exception:
        return ZoneInfo("UTC")


def now_local() -> datetime:
    """Get current datetime in local timezone."""
    return datetime.now(get_local_tz())


def today_local() -> date:
    """Get today's date in local timezone."""
    return now_local().date()


def tomorrow_local() -> date:
    """Get tomorrow's date in local timezone."""
    return today_local() + timedelta(days=1)


def start_of_day(dt_date: date) -> datetime:
    """Get datetime at start of day (midnight) for given date."""
    return datetime.combine(dt_date, time.min, tzinfo=get_local_tz())


def iso_start_of_day(dt_date: date) -> str:
    """Get ISO formatted datetime string for start of given date."""
    return start_of_day(dt_date).isoformat()
