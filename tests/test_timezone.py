"""Tests for timezone-aware headers, formatting, and resolution."""

import pytest
import datetime as dt
from unittest.mock import patch
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from standup.timezone_helper import resolve_timezone
from standup.formatter import _now_header


def test_resolve_timezone_canonical_utc():
    """Verify UTC, Etc/UTC, GMT, Z work without calling zoneinfo."""
    # We mock ZoneInfo to always raise ZoneInfoNotFoundError to prove they don't depend on it
    with patch("zoneinfo.ZoneInfo", side_effect=ZoneInfoNotFoundError("Mocked no database")):
        assert resolve_timezone("UTC") == dt.timezone.utc
        assert resolve_timezone("Etc/UTC") == dt.timezone.utc
        assert resolve_timezone("GMT") == dt.timezone.utc
        assert resolve_timezone("Z") == dt.timezone.utc
        assert resolve_timezone("  utc  ") == dt.timezone.utc


def test_resolve_timezone_iana():
    """Verify normal IANA timezone values resolve using ZoneInfo."""
    tz_istanbul = resolve_timezone("Europe/Istanbul")
    assert tz_istanbul is not None
    assert isinstance(tz_istanbul, ZoneInfo)
    assert tz_istanbul.key == "Europe/Istanbul"

    tz_ny = resolve_timezone("America/New_York")
    assert tz_ny is not None
    assert isinstance(tz_ny, ZoneInfo)
    assert tz_ny.key == "America/New_York"


def test_resolve_timezone_invalid():
    """Verify invalid timezones raise ValueError containing configured timezone."""
    with pytest.raises(ValueError) as excinfo:
        resolve_timezone("Invalid/Zone")
    assert "Invalid timezone 'Invalid/Zone'" in str(excinfo.value)
    assert "timezone data is unavailable" in str(excinfo.value)


def test_timezone_istanbul_formatting():
    """Verify Europe/Istanbul timezone offsets work and show correct date/time."""
    # Fixed UTC datetime: 2026-07-06 22:30:00 UTC
    # In Europe/Istanbul (UTC+3), it will be 2026-07-07 01:30:00
    fixed_utc = dt.datetime(2026, 7, 6, 22, 30, 0, tzinfo=dt.timezone.utc)
    tz_istanbul = resolve_timezone("Europe/Istanbul")

    header_istanbul = _now_header(tz=tz_istanbul, now=fixed_utc)
    assert header_istanbul == "2026-07-07 (Tuesday)"


def test_timezone_new_york_formatting():
    """Verify America/New_York timezone offsets work and show correct date/time."""
    # Fixed UTC datetime: 2026-07-06 01:30:00 UTC
    # In America/New_York (UTC-4 in DST/July), it will be 2026-07-05 21:30:00
    fixed_utc = dt.datetime(2026, 7, 6, 1, 30, 0, tzinfo=dt.timezone.utc)
    tz_ny = resolve_timezone("America/New_York")

    header_ny = _now_header(tz=tz_ny, now=fixed_utc)
    assert header_ny == "2026-07-05 (Sunday)"


def test_timezone_naive_injected():
    """Verify naive datetime defaults to UTC and is converted correctly."""
    naive_dt = dt.datetime(2026, 7, 6, 23, 30, 0)  # Naive
    tz_istanbul = resolve_timezone("Europe/Istanbul")
    # UTC 23:30 -> Istanbul (+3) -> 02:30 next day
    header = _now_header(tz=tz_istanbul, now=naive_dt)
    assert header == "2026-07-07 (Tuesday)"


def test_default_config_timezoneinfo_works():
    """Verify the default configuration works (defaults to UTC)."""
    tz = resolve_timezone("UTC")
    assert tz == dt.timezone.utc

    # Verify header formatting with UTC default
    fixed_utc = dt.datetime(2026, 7, 6, 12, 0, 0, tzinfo=dt.timezone.utc)
    header = _now_header(tz=tz, now=fixed_utc)
    assert header == "2026-07-06 (Monday)"
