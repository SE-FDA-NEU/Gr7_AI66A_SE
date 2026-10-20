"""Helpers for timestamps stored in UTC and entered in Vietnam local time."""

from datetime import datetime, timedelta, timezone

TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S"
LOCAL_INPUT_FORMAT = "%Y-%m-%dT%H:%M"
VIETNAM_TIME = timezone(timedelta(hours=7))


def utc_now_naive() -> datetime:
    """Return the current UTC time without tzinfo, matching the database format."""
    return datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None)


def parse_utc_timestamp(value: str) -> datetime:
    """Parse a UTC timestamp stored without an explicit offset."""
    return datetime.strptime(value, TIMESTAMP_FORMAT)


def local_input_to_utc(value: str) -> str:
    """Convert a datetime-local value in UTC+7 to the UTC database format."""
    local_time = datetime.strptime(value, LOCAL_INPUT_FORMAT).replace(tzinfo=VIETNAM_TIME)
    return local_time.astimezone(timezone.utc).replace(tzinfo=None).strftime(TIMESTAMP_FORMAT)


def utc_timestamp_to_local_input(value: str | None) -> str:
    """Convert a stored UTC timestamp to a value suitable for datetime-local."""
    if not value:
        return ""
    utc_time = parse_utc_timestamp(value).replace(tzinfo=timezone.utc)
    return utc_time.astimezone(VIETNAM_TIME).strftime(LOCAL_INPUT_FORMAT)


def format_vietnam_time(value: str) -> str:
    """Format a stored UTC timestamp for display in Vietnam time."""
    utc_time = parse_utc_timestamp(value).replace(tzinfo=timezone.utc)
    return utc_time.astimezone(VIETNAM_TIME).strftime("%d %b %Y, %H:%M (UTC+7)")
