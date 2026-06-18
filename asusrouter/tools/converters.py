"""Converters module.

This module has methods to convert data between different formats
without complicated logic. In case data cannot be converted,
`None` is returned and no exception is raised.

If data conversion requires complicated logic,
it should be in the Readers module
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, TypeVar, cast

from asusrouter.tools.cleaners import clean_content
from asusrouter.tools.converters_v2.raw import raw_to_int

_T = TypeVar("_T")
_E = TypeVar("_E", bound=Enum)


# TODO: remove for v2 (inline string cleaning in each v2 function)
def clean_input(func: Callable[..., Any]) -> Callable[..., Any]:
    """Clean input data."""

    def wrapper(content: Any, *args: Any, **kwargs: Any) -> Any:
        """Return a clean input data before passing it to the function."""

        if isinstance(content, str):
            return func(clean_string(content), *args, **kwargs)
        return func(content, *args, **kwargs)

    return wrapper


# TODO: migrate to v2: converters_v2/raw.py (raw_to_int)
def clean_jitter(value: _T, jitter: int = 1) -> int | _T:
    """Clean jitter from an integer value.

    If input is int-compatible, remove unwanted jitter
    `jitter` by lowering value resolution. If any other
    non-compatible value is given, return it unchanged.
    """

    vint = raw_to_int(value)
    _jitter = raw_to_int(jitter)
    jint = _jitter if _jitter is not None else 1
    if isinstance(vint, int) and jint > 0:
        block_size = 2 * jint + 1
        return int(vint - (vint % block_size) + jint)

    return value


# TODO: replace for v2: raw_to_str in converters_v2/raw.py
def clean_string(content: str | None) -> str | None:
    """Get a clean string or return None if it is empty."""

    # Not a string
    if not content or not isinstance(content, str):
        return None

    content = clean_content(content.strip())
    # Empty string
    if not content:
        return None

    return content


# TODO: migrate to v2: converters_v2/dict.py
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


# TODO: remove for v2 (v1 pipeline specific)
def get_arguments(
    args: str | tuple[str, ...], **kwargs: Any
) -> Any | tuple[Any | None, ...]:
    """Get the arguments from kwargs."""

    # Make sure args is a tuple
    if not isinstance(args, tuple):
        args = (args,)

    arguments = kwargs.get("arguments", {})

    found_args: list[Any | None] = []

    for arg in args:
        # Skip if not a string
        if not isinstance(arg, str):
            continue
        # Get the arg and save to found_args
        arg_value = arguments.get(arg) if arguments else kwargs.get(arg)
        found_args.append(arg_value)

    if len(found_args) == 1:
        return found_args[0]

    return tuple(found_args) if found_args else None


# TODO: remove for v2 (superseded by from_value() mixin on v2 enums)
def get_enum_key_by_value(
    enum: type[_E], value: Any, default: _E | None = None
) -> _E:
    """Get the enum key by value."""

    if issubclass(enum, Enum):
        for enum_value in enum:
            if enum_value.value == value:
                return enum_value

    if default is not None:
        return default

    raise ValueError(f"Invalid value: {value}")


# TODO: migrate to v2: converters_v2/dict.py
def list_from_dict(raw: dict[Any, Any] | list[Any] | None) -> list[str]:
    """Return dictionary keys as list."""

    if isinstance(raw, list):
        return raw

    if not isinstance(raw, dict):
        return []

    return list(raw.keys())


# TODO: remove for v2 (v1 protocol specific)
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


# TODO: remove for v2 (v1 pipeline specific)
def run_method(
    value: Any, method: Callable[..., Any] | list[Callable[..., Any]] | None
) -> Any:
    """Run a method or a list of methods on a value and return the result."""

    if not method:
        return value

    if not isinstance(method, list):
        method = [method]

    for func in method:
        if isinstance(func, type) and issubclass(func, Enum):
            try:
                value = func(value)
            except ValueError:
                value = func.UNKNOWN if hasattr(func, "UNKNOWN") else None
        else:
            value = func(value)

    return value


# TODO: migrate to v2: converters_v2/datetime.py
@clean_input
def safe_datetime(content: str | None) -> datetime | None:
    """Read the content as datetime or return None."""

    if not content:
        return None

    try:
        return datetime.fromisoformat(content)
    except (ValueError, TypeError):
        try:
            return datetime.strptime(content, "%a, %d %b %Y %H:%M:%S %z")
        except (ValueError, TypeError):
            return None


# TODO: remove for v2 (superseded by from_value() mixin on v2 enums)
def safe_enum(
    enum: type[_E],
    value: Any,
    default_value: Any | None = None,
    default: _E | None = None,
) -> _E | None:
    """Get the enum key by value."""

    # Fast return
    # Return the default enum member
    if not default_value and not value and default is not None:
        return default

    if issubclass(enum, Enum):
        _def_enum_value = None
        # Go through the enum values
        for enum_value in enum:
            # Check for the value
            if enum_value.value == value:
                # Fast return
                return enum_value
            # Check for the default value
            if enum_value.value == default_value:
                _def_enum_value = enum_value
        # Return the default value
        if _def_enum_value is not None:
            return _def_enum_value

    return None


# TODO: migrate to v2: converters_v2/raw.py
@clean_input
def safe_exists(content: str | None) -> bool:
    """Read the content as boolean or return None."""

    return content is not None


# TODO: migrate to v2: converters_v2/str.py
def safe_list(content: Any) -> list[Any]:
    """Read any content as a list."""

    if isinstance(content, list):
        return content

    if content is None:
        return []

    return [content]


# TODO: migrate to v2: converters_v2/str.py
def safe_list_csv(content: str | None) -> list[str]:
    """Read the list as comma separated values."""

    return safe_list_from_string(content, ",")


# TODO: migrate to v2: converters_v2/str.py
@clean_input
def safe_list_from_string(
    content: str | None, delimiter: str = " "
) -> list[str]:
    """Read the content as list or return empty list."""

    if not isinstance(content, str):
        return []

    return content.split(delimiter)


# TODO: remove for v2 (v1 pipeline specific)
@clean_input
def safe_return(content: Any) -> Any:
    """Return the content."""

    return content


# TODO: migrate to v2: converters_v2/raw.py (raw_to_float)
def safe_speed(
    current: (float),
    previous: (float),
    time_delta: float | None = None,
) -> float:
    """Calculate speed.

    Allows calculation only of positive speed, otherwise returns 0.0.
    """

    if time_delta is None or time_delta == 0.0:
        return 0.0

    diff = current - previous if current > previous else 0.0

    return diff / time_delta


# TODO: migrate to v2: converters_v2/datetime.py
def safe_time_from_delta(content: str) -> datetime:
    """Transform time delta to the date in the past."""

    return datetime.now(UTC).replace(
        microsecond=0, tzinfo=UTC
    ) - safe_timedelta_long(content)


# TODO: migrate to v2: converters_v2/datetime.py
@clean_input
def safe_timedelta_long(content: str | None) -> timedelta:
    """Transform connection timedelta.

    Transform timedelta of the device to a proper datetime object
    when the device was connected.
    """

    if not content:
        return timedelta()

    part = content.split(":")
    try:
        return timedelta(
            hours=int(part[-3]), minutes=int(part[-2]), seconds=int(part[-1])
        )
    except (ValueError, IndexError):
        return timedelta()


# TODO: remove for v2 (v1 pipeline specific)
def safe_unpack_key(
    content: tuple[str, Callable[..., Any] | None | list[Callable[..., Any]]]
    | str
    | tuple[str],
) -> tuple[str, Callable[..., Any] | list[Callable[..., Any]] | None]:
    """Unpack a (key, method) tuple, returning (key, None) for bare strings."""

    if isinstance(content, tuple):
        key = content[0]
        if len(content) > 1:
            content = cast(
                tuple[
                    str,
                    Callable[..., Any] | None | list[Callable[..., Any]],
                ],
                content,
            )
            methods = content[1]
            if methods is not None and not (
                callable(methods) or isinstance(methods, Iterable)
            ):
                methods = None
        else:
            methods = None
        return key, methods

    # No method selected
    return content, None


# TODO: remove for v2 (v1 pipeline specific)
def safe_unpack_keys(
    content: tuple[str, str, Any] | tuple[str, str] | str,
) -> tuple[Any, ...]:
    """Unpack key/key_to_use/method tuple even if some values are missing."""

    _full = 3  # (key, key_to_use, method)
    _partial = 2  # (key, key_to_use)
    if isinstance(content, tuple):
        # All 3 values are present
        if len(content) == _full:
            return content

        # No method selected
        if len(content) == _partial:
            return content + (None,)

    # No method and key_to_use selected
    # We need to replace key_to_use with key
    new_content = (content, content)
    return new_content + (None,)


# TODO: migrate to v2: converters_v2/raw.py (raw_to_float)
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


# TODO: migrate to v2: converters_v2/raw.py (raw_to_float)
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


# TODO: migrate to v2: converters_v2/datetime.py
def safe_timestamp_to_utc(value: int | None) -> datetime | None:
    """Convert timestamp to UTC datetime."""

    if value is None:
        return None

    try:
        return datetime.fromtimestamp(value, UTC)
    except (OverflowError, ValueError, TypeError, OSError):
        try:
            return datetime.fromtimestamp(value / 1000, UTC)
        except (OverflowError, ValueError, TypeError, OSError):
            return None


# TODO: migrate to v2: converters_v2/datetime.py
def safe_utc_to_timestamp(value: datetime | None) -> float | None:
    """Convert UTC datetime to timestamp."""

    if value is None or not isinstance(value, datetime):
        return None

    return value.timestamp()


# TODO: migrate to v2: converters_v2/datetime.py
def safe_utc_to_timestamp_milli(value: datetime | None) -> int | None:
    """Convert UTC datetime to timestamp in milliseconds."""

    _timestamp = safe_utc_to_timestamp(value)

    if _timestamp is None:
        return None

    return int(_timestamp * 1000)


# TODO: migrate to v2: converters_v2/raw.py (raw_to_int)
def scale_value_int(
    value: int,
    scale: int,
    scale_from: int | None = None,
) -> int:
    """Scale the value from the custom scale."""

    if scale_from is None or scale_from == scale:
        return value

    return (
        min(round(value * scale / scale_from), scale) if scale_from != 0 else 0
    )
