"""Log timestamp resolution for AsusRouter."""

from __future__ import annotations

from datetime import datetime, timedelta, tzinfo

from asusrouter.modules.log.entry import ARLogEntry

# `<hh>:<mm>:<ss>`
_CLOCK_PARTS = 3
_MONTHS = {
    name: number
    for number, name in enumerate(
        (
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ),
        start=1,
    )
}

# `<Mon> <day> <hh>:<mm>:<ss>`
_STAMP_PARTS = 3

_YEAR_WRAP_MONTHS = 2

_FUTURE_GRACE = timedelta(days=1)


def _parse_stamp(timestamp_str: str) -> tuple[int, int, int, int, int] | None:
    """Parse a stamp into (month, day, hour, minute, second) or None."""

    # Splitting beats a regex on a stamp per entry
    parts = timestamp_str.split()
    if len(parts) != _STAMP_PARTS:
        return None

    month = _MONTHS.get(parts[0])
    if month is None:
        return None

    clock = parts[2].split(":")
    if len(clock) != _CLOCK_PARTS:
        return None

    try:
        return (
            month,
            int(parts[1]),
            int(clock[0]),
            int(clock[1]),
            int(clock[2]),
        )
    except ValueError:
        return None


def _host_fallback(entries: list[ARLogEntry]) -> tuple[int, tzinfo | None]:
    """Use host clock data if no device clock is available."""

    now = datetime.now().astimezone()
    year = now.year

    for entry in reversed(entries):
        parts = _parse_stamp(entry.timestamp_str)
        if parts is None:
            continue
        try:
            newest = datetime(year, *parts, tzinfo=now.tzinfo)
        except ValueError:
            continue
        if newest > now + _FUTURE_GRACE:
            year -= 1
        break

    return year, now.tzinfo


def resolve_datetimes(
    entries: list[ARLogEntry], anchor: datetime | None = None
) -> list[ARLogEntry]:
    """Fill each entry's `timestamp` against the device's own clock."""

    if not entries:
        return entries

    year: int
    zone: tzinfo | None
    # Use device anchor, or fall back to the host
    if anchor is not None and anchor.tzinfo is not None:
        year, zone = anchor.year, anchor.tzinfo
    else:
        year, zone = _host_fallback(entries)
    newer_month: int | None = None

    # Newest entry is last; walk back to oldest
    for index in range(len(entries) - 1, -1, -1):
        entry = entries[index]
        parts = _parse_stamp(entry.timestamp_str)
        if parts is None:
            continue

        month, day, hour, minute, second = parts
        if (
            newer_month is not None
            and month - newer_month >= _YEAR_WRAP_MONTHS
        ):
            year -= 1
        newer_month = month

        try:
            stamp = datetime(
                year, month, day, hour, minute, second, tzinfo=zone
            )
        except ValueError:
            continue

        object.__setattr__(entry, "timestamp", stamp)

    return entries
