"""Timezone resolution helper."""

from __future__ import annotations

import datetime
import zoneinfo

# Canonical UTC timezone names that can be resolved without external database
UTC_NAMES = {"UTC", "ETC/UTC", "GMT", "Z"}


def resolve_timezone(tz_name: str | None) -> datetime.tzinfo | None:
    """Resolve a timezone name into a tzinfo object.

    If the timezone name is empty, returns None.
    If it is a canonical UTC timezone, returns datetime.timezone.utc.
    Otherwise, attempts to resolve it using zoneinfo.ZoneInfo.

    Raises ValueError with a user-friendly message if the timezone is invalid
    or if the timezone data is unavailable.
    """
    if not tz_name:
        return None

    normalized = tz_name.strip().upper()
    if normalized in UTC_NAMES:
        return datetime.timezone.utc

    try:
        return zoneinfo.ZoneInfo(tz_name)
    except zoneinfo.ZoneInfoNotFoundError as e:
        raise ValueError(
            f"Invalid timezone '{tz_name}' in configuration or timezone data is unavailable.\n"
            f"Please verify it is a valid IANA timezone name. On Windows, you may need to ensure 'tzdata' is installed."
        ) from e
