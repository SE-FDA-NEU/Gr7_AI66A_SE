"""Chuyển đổi thời gian giữa UTC lưu trong DB và UTC+7 hiển thị/nhập ở Việt Nam."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone

TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S"
LOCAL_INPUT_FORMAT = "%Y-%m-%dT%H:%M"
VIETNAM_TIME = timezone(timedelta(hours=7))


def utc_now_naive() -> datetime:
    """Return the current UTC time without tzinfo, matching the database format."""
    # Bỏ múi giờ và microsecond để khớp định dạng timestamp đang lưu trong DB.
    return datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None)


def parse_utc_timestamp(value: str) -> datetime:
    """Parse a UTC timestamp stored without an explicit offset."""
    return datetime.strptime(value, TIMESTAMP_FORMAT)


def local_input_to_utc(value: str) -> str:
    """Convert a datetime-local value in UTC+7 to the UTC database format."""
    # datetime-local không gửi timezone, nên gắn UTC+7 trước khi đổi sang UTC.
    local_time = datetime.strptime(value, LOCAL_INPUT_FORMAT).replace(tzinfo=VIETNAM_TIME)
    return local_time.astimezone(timezone.utc).replace(tzinfo=None).strftime(TIMESTAMP_FORMAT)


def utc_timestamp_to_local_input(value: str | None) -> str:
    """Convert a stored UTC timestamp to a value suitable for datetime-local."""
    # Input trống được trả về nguyên dạng để form hiển thị trường rỗng.
    if not value:
        return ""
    utc_time = parse_utc_timestamp(value).replace(tzinfo=timezone.utc)
    return utc_time.astimezone(VIETNAM_TIME).strftime(LOCAL_INPUT_FORMAT)


def format_vietnam_time(value: str) -> str:
    """Format a stored UTC timestamp for display in Vietnam time."""
    # Gắn UTC cho timestamp từ DB, rồi đổi sang múi giờ dùng trong giao diện.
    utc_time = parse_utc_timestamp(value).replace(tzinfo=timezone.utc)
    return utc_time.astimezone(VIETNAM_TIME).strftime("%d %b %Y, %H:%M (UTC+7)")
