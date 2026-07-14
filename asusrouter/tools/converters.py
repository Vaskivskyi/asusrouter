"""Converters module.

This module has methods to convert data between different formats
without complicated logic. In case data cannot be converted,
`None` is returned and no exception is raised.

If data conversion requires complicated logic,
it should be in the Readers module
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any

from asusrouter.tools.converters_v2.raw import raw_to_str


def flatten_dict(
    d: dict[Any, Any] | None,
    parent_key: str = "",
    sep: str = "_",
    exclude: str | Iterable[str] | None = None,
) -> dict[str, Any] | None:
    """Flatten a nested dictionary."""

    if d is None:
        return None

    if not isinstance(d, dict):
        return {}

    items = []
    exclude = (exclude,) if isinstance(exclude, str) else tuple(exclude or [])
    for k, v in d.items():
        new_key = (
            f"{parent_key}{sep}{k}" if parent_key not in ("", None) else k
        )
        # We have a dict - check it
        if isinstance(v, dict):
            # This key should be skipped
            if isinstance(new_key, str) and new_key.endswith(exclude):
                items.append((new_key, v))
                continue
            # Go recursive
            flattened = flatten_dict(v, new_key, sep, exclude)
            if flattened is not None:
                items.extend(flattened.items())
            continue
        # Not a dict - add it
        items.append((new_key, v))
    return dict(items)


def nvram_get(
    content: list[str] | str | None,
) -> list[tuple[str, ...]] | None:
    """Convert values to NVRAM request."""

    if not content:
        return None

    if not isinstance(content, list | str):
        content = str(content)

    if isinstance(content, str):
        content = [content]

    return [("nvram_get", value) for value in content]


def safe_datetime(content: str | None) -> datetime | None:
    """Read the content as datetime or return None."""

    content = raw_to_str(content)
    if not content:
        return None

    try:
        return datetime.fromisoformat(content)
    except (ValueError, TypeError):
        try:
            return datetime.strptime(content, "%a, %d %b %Y %H:%M:%S %z")
        except (ValueError, TypeError):
            return None


def safe_list_from_string(
    content: str | None, delimiter: str = " "
) -> list[str]:
    """Read the content as list or return empty list."""

    content = raw_to_str(content)
    if not isinstance(content, str):
        return []

    return content.split(delimiter)


def safe_time_from_delta(content: str) -> datetime:
    """Transform time delta to the date in the past."""

    return datetime.now(UTC).replace(
        microsecond=0, tzinfo=UTC
    ) - safe_timedelta_long(content)


def safe_timedelta_long(content: str | None) -> timedelta:
    """Transform connection timedelta.

    Transform timedelta of the device to a proper datetime object
    when the device was connected.
    """

    content = raw_to_str(content)
    if not content:
        return timedelta()

    part = content.split(":")
    try:
        return timedelta(
            hours=int(part[-3]), minutes=int(part[-2]), seconds=int(part[-1])
        )
    except (ValueError, IndexError):
        return timedelta()


def safe_usage(used: float, total: float) -> float:
    """Calculate usage in percents.

    Allows calculation only of positive usage, otherwise returns 0.0.
    """

    if total == 0:
        return 0.0

    usage = round(used / total * 100, 2)

    # Don't allow negative usage
    if usage < 0:
        return 0.0

    return usage


def safe_usage_historic(
    used: float,
    total: float,
    prev_used: float,
    prev_total: float,
) -> float:
    """Calculate usage in percents for difference between values.

    This method is just an interface to calculate usage using `usage` method
    """

    used_diff = used - prev_used
    total_diff = total - prev_total

    # Don't allow negative differences
    if used_diff < 0 or total_diff < 0:
        return 0.0

    return safe_usage(used_diff, total_diff)
