import os
from datetime import date, datetime, time, timedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

_DEFAULT_TZ_NAME = os.getenv("DEFAULT_TIMEZONE", "Europe/Zurich")


def get_local_tz() -> ZoneInfo:
    try:
        return ZoneInfo(_DEFAULT_TZ_NAME)
    except Exception:
        return ZoneInfo("UTC")


def now_local() -> datetime:
    return datetime.now(get_local_tz())


def today_local() -> date:
    return now_local().date()


def tomorrow_local() -> date:
    return today_local() + timedelta(days=1)


def start_of_day(dt_date: date) -> datetime:
    return datetime.combine(dt_date, time.min, tzinfo=get_local_tz())


def iso_start_of_day(dt_date: date) -> str:
    return start_of_day(dt_date).isoformat()
