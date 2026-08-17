"""Time helpers for webhook retry scheduling."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def parse_instant(value: str) -> datetime:
    """Parse a UTC ISO-8601 instant ending in Z into an aware datetime."""
    if not value.endswith("Z"):
        raise ValueError("timestamp must be UTC with Z suffix")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt.astimezone(timezone.utc)


def add_milliseconds(instant: datetime, delay_ms: int) -> datetime:
    """Advance an aware datetime by an integer number of milliseconds."""
    if instant.tzinfo is None:
        raise ValueError("instant must be timezone-aware")
    return instant + timedelta(milliseconds=delay_ms)


def format_instant(instant: datetime) -> str:
    """Format an aware datetime as UTC ISO-8601 with millisecond precision."""
    utc = instant.astimezone(timezone.utc)
    text = utc.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    return text
