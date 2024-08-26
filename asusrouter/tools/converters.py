"""Converters module

This module has methods to convert data between different formats
without complicated logic. In case data cannot be converted,
`None` is returned and no exception is raised.

If data conversion requires complicated logic,
it should be in the Readers module"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Iterable, Optional, Type, TypeVar, cast

from dateutil.parser import parse as dtparse

from asusrouter.tools.cleaners import clean_content

true_values = {"true", "allow", "1", "on", "enabled"}
false_values = {"false", "block", "0", "off", "disabled"}


_T = TypeVar("_T")
_E = TypeVar("_E", bound=Enum)


def clean_input(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to clean input data."""

    def wrapper(content: Any, *args, **kwargs) -> Any:
        if isinstance(content, str):
            return func(clean_string(content), *args, **kwargs)
        return func(content, *args, **kwargs)

    return wrapper


def clean_string(content: Optional[str]) -> Optional[str]:
    """Get a clean string or return None if it is empty."""

    # Not a string
    if not content or not isinstance(content, str):
        return None

    content = clean_content(content.strip())
    # Empty string
    if not content:
        return None

    return content


def flatten_dict(
    d: Optional[dict[Any, Any]],
    parent_key: str = "",
    sep: str = "_",
    exclude: Optional[str | Iterable[str]] = None,
) -> Optional[dict[str, Any]]:
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


def get_arguments(
    args: str | tuple[str, ...], **kwargs: Any
) -> Any | tuple[Optional[Any], ...]:
    """Get the arguments from kwargs."""

    # Make sure args is a tuple
    if not isinstance(args, tuple):
        args = (args,)

    arguments = kwargs.get("arguments", {})

    found_args: list[Optional[Any]] = []

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


def get_enum_key_by_value(
    enum: Type[_E], value: Any, default: Optional[_E] = None
) -> _E:
    """Get the enum key by value"""

    if issubclass(enum, Enum):
        for enum_value in enum:
            if enum_value.value == value:
                return enum_value

    if default is not None:
        return default

    raise ValueError(f"Invalid value: {value}")


def handle_none_content(
    content: Optional[_T], default: Optional[_T]
) -> Optional[_T]:
    """Return the default value if content is None, else return the content."""

    if content is None:
        return default
    return content


def int_as_bits(value: int) -> list[bool]:
    """Convert an integer to a list of bits."""

    if not isinstance(value, int):
        return []

    # Negative values are not supported
    if value < 0:
        return []

    # Zero is a special case
    if value == 0:
        return [False]

    return [bool(value & (1 << i)) for i in range(value.bit_length())]


def int_as_capabilities(
    value: int, capabilities: Type[Enum]
) -> dict[Enum, bool]:
    """Convert an integer to a dict of capabilities."""

    # Check if the capabilities is an enum
    if not is_enum(capabilities) or not isinstance(value, int):
        return {}

    # Convert the value to a list of bits
    bits = int_as_bits(value)

    result = {}

    # For each capability in the capabilities
    # Considering key as a capability name and value as a capability bit
    for capability in capabilities:
        # Check that the capability is an integer
        if not isinstance(capability.value, int):
            continue

        # Check if the bit is set
        result[capability] = (
            bits[capability.value] if capability.value < len(bits) else False
        )

    return result


def is_enum(v) -> bool:
    """Check if the value is an enum."""

    return isinstance(v, type) and issubclass(v, Enum)


def list_from_dict(raw: Optional[dict[Any, Any] | list[Any]]) -> list[str]:
    """Return dictionary keys as list."""

    if isinstance(raw, list):
        return raw

    if not isinstance(raw, dict):
        return []

    return list(raw.keys())


def nvram_get(
    content: Optional[list[str] | str],
) -> Optional[list[tuple[str, ...]]]:
    """Convert values to NVRAM request."""

    if not content:
        return None

    if not isinstance(content, (list, str)):
        content = str(content)

    if isinstance(content, str):
        content = [content]

    return [("nvram_get", value) for value in content]


def run_method(
    value: Any, method: Optional[Callable[..., Any] | list[Callable[..., Any]]]
) -> Any:
    """Run a method or a list of methods on a value and return the result."""

    if not method:
        return value

    if not isinstance(method, list):
        method = [method]

    for func in method:
        if is_enum(func):
            try:
                value = func(value)
            except ValueError:
                value = func.UNKNOWN if hasattr(func, "UNKNOWN") else None
        else:
            value = func(value)

    return value


@clean_input
def safe_bool(content: Optional[str | int | float | bool]) -> Optional[bool]:
    """Read the content as boolean or return None."""

    if content is None:
        return None

    if isinstance(content, bool):
        return content
    if isinstance(content, (int, float)):
        return content != 0
    if isinstance(content, str):
        content = content.lower()
        if content in true_values:
            return True
        if content in false_values:
            return False

    return None


def safe_convert(
    convert_func: Callable[[str | int | float], _T],
    content: Optional[str | int | float],
    default: Optional[_T] = None,
    fallback_func: Optional[Callable[[Any], _T]] = None,
) -> Optional[_T]:
    """Try to convert the content using the conversion function,
    return the default value if it fails."""

    if content is None:
        return default
    try:
        return convert_func(content)
    except ValueError:
        if fallback_func is not None and isinstance(content, str):
            try:
                return fallback_func(content)
            except ValueError:
                pass
        return default


@clean_input
def safe_datetime(content: Optional[str]) -> Optional[datetime]:
    """Read the content as datetime or return None."""

    if not content:
        return None

    try:
        return dtparse(content)
    except (ValueError, TypeError):
        return None


def safe_enum(
    enum: Type[_E],
    value: Any,
    default_value: Optional[Any] = None,
    default: Optional[_E] = None,
) -> Optional[_E]:
    """Get the enum key by value"""

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


@clean_input
def safe_exists(content: Optional[str]) -> bool:
    """Read the content as boolean or return None."""

    if content is None:
        return False

    return True


@clean_input
def safe_float(
    content: Optional[str | int | float], default: Optional[float] = None
) -> Optional[float]:
    """Read the content as float or return None."""

    content = cast(
        Optional[str | int | float], handle_none_content(content, default)
    )
    return safe_convert(float, content, default)


@clean_input
def safe_int(
    content: Optional[str | int | float],
    default: Optional[int] = None,
    base: int = 10,
) -> Optional[int]:
    """Read the content as int or return the default value (None if not specified)."""

    content = cast(
        Optional[str | int | float], handle_none_content(content, default)
    )
    if isinstance(content, str):
        return safe_convert(
            lambda x: int(x, base=base),
            content,
            default,
            lambda x: int(float(x)),
        )
    return safe_convert(
        int, content, default if isinstance(default, int) else None
    )


def safe_list(content: Any) -> list[Any]:
    """Read any content as a list."""

    if isinstance(content, list):
        return content

    if content is None:
        return []

    return [content]


def safe_list_csv(content: Optional[str]) -> list[str]:
    """Read the list as comma separated values."""

    return safe_list_from_string(content, ",")


@clean_input
def safe_list_from_string(
    content: Optional[str], delimiter: str = " "
) -> list[str]:
    """Read the content as list or return empty list."""

    if not isinstance(content, str):
        return []

    return content.split(delimiter)


@clean_input
def safe_return(content: Any) -> Any:
    """Return the content."""

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

    return datetime.now(timezone.utc).replace(
        microsecond=0, tzinfo=timezone.utc
    ) - safe_timedelta_long(content)


@clean_input
def safe_timedelta_long(content: Optional[str]) -> timedelta:
    """Transform connection timedelta of the device to a proper
    datetime object when the device was connected"""

    if not content:
        return timedelta()

    part = content.split(":")
    try:
        return timedelta(
            hours=int(part[-3]), minutes=int(part[-2]), seconds=int(part[-1])
        )
    except (ValueError, IndexError):
        return timedelta()


def safe_unpack_key(
    content: tuple[
        str, Optional[Callable[..., Any]] | list[Callable[..., Any]]
    ]
    | str
    | tuple[str],
) -> tuple[str, Optional[Callable[..., Any] | list[Callable[..., Any]]]]:
    """
    Unpacks a tuple containing a key and a method.

    The input can be a tuple of a string and a method, a single string,
    or a single-item tuple with a string.
    If the input is a string or a single-item tuple, the returned method is None.
    If the input is a tuple of a string and a method, both are returned as is.

    Args:
        content: A tuple of a string and a method, a single string,
        or a single-item tuple with a string.

    Returns:
        A tuple containing a string and a method.
        If no method was provided in the input, None is returned as the method.
    """

    if isinstance(content, tuple):
        key = content[0]
        if len(content) > 1:
            content = cast(
                tuple[
                    str,
                    Optional[Callable[..., Any]] | list[Callable[..., Any]],
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


def safe_unpack_keys(
    content: tuple[
        str, str, Optional[Callable[..., Any]] | list[Callable[..., Any]]
    ]
    | tuple[str, str]
    | str,
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
    new_content = (content, content)
    return new_content + (None,)


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

    used_diff = used - prev_used
    total_diff = total - prev_total

    # Don't allow negative differences
    if used_diff < 0 or total_diff < 0:
        return 0.0

    return safe_usage(used_diff, total_diff)


def safe_timestamp_to_utc(value: Optional[int]) -> Optional[datetime]:
    """Convert timestamp to UTC datetime."""

    if value is None:
        return None

    try:
        return datetime.fromtimestamp(value, timezone.utc)
    except (ValueError, TypeError, OSError):
        try:
            return datetime.fromtimestamp(value / 1000, timezone.utc)
        except (ValueError, TypeError, OSError):
            return None


def safe_utc_to_timestamp(value: Optional[datetime]) -> Optional[float]:
    """Convert UTC datetime to timestamp."""

    if value is None or not isinstance(value, datetime):
        return None

    return value.timestamp()


def safe_utc_to_timestamp_milli(value: Optional[datetime]) -> Optional[int]:
    """Convert UTC datetime to timestamp in milliseconds."""

    _timestamp = safe_utc_to_timestamp(value)

    if _timestamp is None:
        return None

    return int(_timestamp * 1000)


def scale_value_int(
    value: int,
    scale: int,
    scale_from: Optional[int] = None,
) -> int:
    """Scale the value from the custom scale."""

    if scale_from is None or scale_from == scale:
        return value

    return (
        min(round(value * scale / scale_from), scale) if scale_from != 0 else 0
    )
