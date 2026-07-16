"""Timemap model and codec for parental control schedules.

A timemap is a `<`-joined string of 12-char entries, each encoding one
weekly window as `[mode][enable][weekday_hex][sH][sM][eH][eM]`:

- `mode`  - `W` offline / `M` online, per-rule (see the schedule mode enum)
- `enable`- per-entry `0`/`1`
- `weekday_hex` - 2 hex digits, one bit per day (bit 0 Sun .. bit 6 Sat)
- `sH sM eH eM` - zero-padded start/end hour and minute; a window that spans
  midnight is stored as a single entry with the end earlier than the start,
  and `eH` may be `24`
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any

from asusrouter.modules.parental_control.enums import (
    ARParentalControlScheduleMode,
    ARWeekday,
)
from asusrouter.tools.readers.nvram_list import decode

_LOGGER = logging.getLogger(__name__)

# Default weekly schedule the web UI seeds a new rule with
DEFAULT_TIMEMAP = "W03E21000700<W04122000800"

_TOKEN_LEN = 12

# Every real weekday, in bit order (UNKNOWN is not a bitmap position)
_WEEKDAYS: tuple[ARWeekday, ...] = tuple(
    day for day in ARWeekday if day is not ARWeekday.UNKNOWN
)

# Common day groups, matching the web UI's Daily/Weekdays/Weekend presets
DAILY = frozenset(_WEEKDAYS)
WEEKDAYS = frozenset(
    {
        ARWeekday.MONDAY,
        ARWeekday.TUESDAY,
        ARWeekday.WEDNESDAY,
        ARWeekday.THURSDAY,
        ARWeekday.FRIDAY,
    }
)
WEEKEND = frozenset({ARWeekday.SUNDAY, ARWeekday.SATURDAY})


@dataclass(frozen=True, kw_only=True)
class ARScheduleEntry:
    """A single weekly schedule window."""

    days: frozenset[ARWeekday] = field(default_factory=frozenset)
    start_hour: int = 0
    start_minute: int = 0
    end_hour: int = 24
    end_minute: int = 0
    enable: bool = True


def timemap_mode(raw: Any) -> ARParentalControlScheduleMode:
    """Read the schedule mode from a timemap's first entry prefix char."""

    return ARParentalControlScheduleMode.from_value(decode(raw)[:1].upper())


def _days_from_bits(bits: int) -> frozenset[ARWeekday]:
    """Expand a weekday bitmap into its set of days."""

    return frozenset(day for day in _WEEKDAYS if bits >> day.value & 1)


def _bits_from_days(days: frozenset[ARWeekday]) -> int:
    """Collapse a set of days into a weekday bitmap."""

    return sum(1 << day.value for day in days)


def _parse_entry(token: str) -> ARScheduleEntry | None:
    """Parse one 12-char timemap entry, or None when it is malformed."""

    if len(token) != _TOKEN_LEN:
        return None
    try:
        return ARScheduleEntry(
            enable=token[1] != "0",
            days=_days_from_bits(int(token[2:4], 16)),
            start_hour=int(token[4:6]),
            start_minute=int(token[6:8]),
            end_hour=int(token[8:10]),
            end_minute=int(token[10:12]),
        )
    except ValueError:
        _LOGGER.debug("Skipping malformed timemap entry: %s", token)
        return None


def parse_timemap(raw: Any) -> list[ARScheduleEntry]:
    """Decode a raw timemap string into its schedule entries."""

    text = decode(raw)
    if not text:
        return []
    entries = [_parse_entry(token) for token in text.split("<")]
    return [entry for entry in entries if entry is not None]


def _serialize_entry(entry: ARScheduleEntry, prefix: str) -> str:
    """Serialize one schedule entry into its 12-char token."""

    return (
        prefix
        + ("1" if entry.enable else "0")
        + f"{_bits_from_days(entry.days):02X}"
        + f"{entry.start_hour:02d}{entry.start_minute:02d}"
        + f"{entry.end_hour:02d}{entry.end_minute:02d}"
    )


def serialize_timemap(
    entries: list[ARScheduleEntry],
    mode: ARParentalControlScheduleMode = (
        ARParentalControlScheduleMode.OFFLINE
    ),
) -> str:
    """Serialize schedule entries into a raw timemap string for the mode."""

    if mode is ARParentalControlScheduleMode.UNKNOWN:
        mode = ARParentalControlScheduleMode.OFFLINE
    return "<".join(_serialize_entry(entry, mode.value) for entry in entries)


def apply_mode(timemap: str, mode: ARParentalControlScheduleMode) -> str:
    """Rewrite each raw timemap entry's prefix char to the given mode."""

    if mode is ARParentalControlScheduleMode.UNKNOWN or not timemap:
        return timemap
    return "<".join(
        mode.value + entry[1:] if entry else entry
        for entry in timemap.split("<")
    )


__all__ = [
    "DAILY",
    "DEFAULT_TIMEMAP",
    "WEEKDAYS",
    "WEEKEND",
    "ARScheduleEntry",
    "apply_mode",
    "parse_timemap",
    "serialize_timemap",
    "timemap_mode",
]
