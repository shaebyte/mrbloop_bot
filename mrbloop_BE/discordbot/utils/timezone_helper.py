import pytz
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

POPULAR_TIMEZONES: list[str] = [
    "Europe/Brussels", "Europe/Amsterdam", "Europe/London",
    "Europe/Paris", "Europe/Berlin", "Europe/Madrid", "Europe/Rome",
    "America/New_York", "America/Chicago", "America/Denver",
    "America/Los_Angeles", "America/Toronto", "America/Sao_Paulo",
    "Asia/Tokyo", "Asia/Shanghai", "Asia/Kolkata",
    "Asia/Dubai", "Asia/Singapore",
    "Australia/Sydney", "Pacific/Auckland", "UTC",
]


def is_valid_timezone(tz_name: str) -> bool:
    try:
        ZoneInfo(tz_name)
        return True
    except (ZoneInfoNotFoundError, KeyError):
        return False


def get_local_now(tz_name: str) -> datetime:
    return datetime.now(pytz.timezone(tz_name))


def is_birthday_time(
    tz_name: str,
    birth_month: int,
    birth_day: int,
    greet_hour: int = 0,
    greet_minute: int = 15,
) -> bool:
    """
    True als het lokaal greet_hour:greet_minute is én vandaag de verjaardag.
    Wordt elke minuut aangeroepen door de scheduler.
    """
    now = get_local_now(tz_name)
    return (
        now.month == birth_month
        and now.day == birth_day
        and now.hour == greet_hour
        and now.minute == greet_minute
    )


def search_timezones(query: str, limit: int = 25) -> list[str]:
    q = query.lower()
    return [tz for tz in pytz.all_timezones if q in tz.lower()][:limit]
