"""Converters module

This module has methods to convert data between different formats 
without complicated logic. In case data cannot be converted, 
`None` is returned and no exception is raised.

If data conversion requires complicated logic, 
it should be in the Readers module"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from dateutil.parser import parse as dtparse


def as_dict(pyobj):
    """Return generator object as dictionary."""

    return dict(pyobj)


def clean_string(content: Optional[str]) -> Optional[str]:
    """Get a clean string or return None if it is empty."""

    # Not a string
    if not content or not isinstance(content, str):
        return None

    content = content.strip()
    # Empty string
    if not content:
        return None

    return content


def flatten_dict(obj: Any, keystring: str = "", delimiter: str = "_"):
    """Flatten dictionary."""

    if isinstance(obj, dict):
        keystring = keystring + delimiter if keystring else keystring
        for key in obj:
            yield from flatten_dict(obj[key], keystring + str(key))
    else:
        yield keystring, obj


def list_from_dict(raw: dict[str, Any]) -> list[str]:
    """Return dictionary keys as list."""

    return list(raw.keys())


def nvram_get(content: Optional[list[str] | str]) -> Optional[list[tuple[str, ...]]]:
    """Convert values to NVRAM request."""

    if not content:
        return None

    if isinstance(content, str):
        content = [content]

    return [("nvram_get", value) for value in content]


def safe_bool(content: Optional[str | int | float | bool]) -> Optional[bool]:
    """Read the content as boolean or return None."""

    result = None

    if content:
        if isinstance(content, bool):
            result = content
        elif isinstance(content, (int, float)):
            result = content != 0
        else:
            content = clean_string(content)
            if content:
                content = content.lower()
                if content in ("true", "allow", "1", "on", "enabled"):
                    result = True
                elif content in ("false", "block", "0", "off", "disabled"):
                    result = False

    return result


def safe_datetime(content: Optional[str]) -> Optional[datetime]:
    """Read the content as datetime or return None."""

    content = clean_string(content)
    if not content:
        return None

    try:
        return dtparse(content)
    except Exception:  # pylint: disable=broad-except
        return None


def safe_exists(content: Optional[str]) -> bool:
    """Read the content as boolean or return None."""

    content = clean_string(content)
    if not content:
        return False

    return True


def safe_float(
    content: Optional[str | int | float], default: Optional[float] = None
) -> Optional[float]:
    """Read the content as float or return None."""

    if isinstance(content, (int, float)):
        return float(content)

    content = clean_string(content)
    if not content:
        return default

    try:
        return float(content)
    except ValueError:
        return default


def safe_int(
    content: Optional[str | int], default: Optional[int] = None, base: int = 10
) -> Optional[int]:
    """Read the content as int or return the default value (None if not specified)."""

    if isinstance(content, int):
        return content

    content = clean_string(content)
    if not content:
        return default if isinstance(default, int) else None

    try:
        return int(content, base=base)
    except ValueError:
        return default if isinstance(default, int) else None


def safe_list(content: Any) -> list[Any]:
    """Read any content as a list."""

    if isinstance(content, list):
        return content

    if content is None:
        return []

    return [content]


def safe_list_from_string(content: Optional[str], delimiter: str = " ") -> list[str]:
    """Read the content as list or return empty list."""

    content = clean_string(content)
    if not content:
        return []

    return content.split(delimiter)


def safe_none_or_str(content: Optional[str]) -> Optional[str]:
    """Read the content as string or return None if it is empty."""

    if content is None or not isinstance(content, str):
        return None

    content = content.strip()
    if content == str():
        return None

    return content


def safe_return(content: Any) -> Any:
    """Return the content."""

    if isinstance(content, str):
        return clean_string(content)

    return content


def safe_speed(
    current: (int | float),
    previous: (int | float),
    time_delta: (int | float) | None = None,
) -> float:
    """Calculate speed.

    Allows calculation only of positive speed, otherwise returns 0.0."""

    if time_delta is None or time_delta == 0.0:
        return 0.0

    diff = current - previous if current > previous else 0.0

    return diff / time_delta


def safe_time_from_delta(content: str) -> datetime:
    """Transform time delta to the date in the past."""

    return datetime.utcnow().replace(
        microsecond=0, tzinfo=timezone.utc
    ) - safe_timedelta_long(content)


def safe_timedelta_long(content: Optional[str]) -> timedelta:
    """Transform connection timedelta of the device to a proper
    datetime object when the device was connected"""

    content = clean_string(content)
    if not content:
        return timedelta()

    part = content.split(":")
    try:
        return timedelta(
            hours=int(part[-3]), minutes=int(part[-2]), seconds=int(part[-1])
        )
    except ValueError:
        return timedelta()


def safe_unpack_key(
    content: tuple[str, Optional[Callable[..., Any]]] | str
) -> tuple[str, Optional[Callable[..., Any]]]:
    """Method to unpack key/method tuple
    even if some values are missing."""

    if isinstance(content, tuple):
        # All 2 values are present
        if len(content) == 2:
            return content

    # No method selected
    return (content, None)


def safe_unpack_keys(
    content: tuple[str, str, Callable[..., Any]] | tuple[str, str] | str
) -> tuple[Any, ...]:
    """Method to unpack key/key_to_use/method tuple
    even if some values are missing."""

    if isinstance(content, tuple):
        # All 3 values are present
        if len(content) == 3:
            return content

        # No method selected
        if len(content) == 2:
            return content + (None,)

    # No method and key_to_use selected
    # We need to replace key_to_use with key
    content = (content, content)
    return content + (None,)


def safe_usage(used: int | float, total: int | float) -> float:
    """Calculate usage in percents.

    Allows calculation only of positive usage, otherwise returns 0.0."""

    if total == 0:
        return 0.0

    usage = round(used / total * 100, 2)

    # Don't allow negative usage
    if usage < 0:
        return 0.0

    return usage


def safe_usage_historic(
    used: int | float,
    total: int | float,
    prev_used: int | float,
    prev_total: int | float,
) -> float:
    """Calculate usage in percents for difference between current and previous values

    This method is just an interface to calculate usage using `usage` method"""

    return safe_usage(used - prev_used, total - prev_total)
