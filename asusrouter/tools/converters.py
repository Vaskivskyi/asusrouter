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

true_values = {"true", "allow", "1", "on", "enabled"}
false_values = {"false", "block", "0", "off", "disabled"}


_T = TypeVar("_T")
_E = TypeVar("_E", bound=Enum)


def clean_input(func: Callable[..., Any]) -> Callable[..., Any]:
    """Clean input data."""

    def wrapper(content: Any, *args: Any, **kwargs: Any) -> Any:
        """Return a clean input data before passing it to the function."""

        if isinstance(content, str):
            return func(clean_string(content), *args, **kwargs)
        return func(content, *args, **kwargs)

    return wrapper


def clean_jitter(value: _T, jitter: int = 1) -> int | _T:
    """Clean jitter from an integer value.

    If input is int-compatible, remove unwanted jitter
    `jitter` by lowering value resolution. If any other
    non-compatible value is given, return it unchanged.
    """

    vint = safe_int(value)
    jint = safe_int(jitter, default=1)
    if isinstance(vint, int) and jint > 0:
        block_size = 2 * jint + 1
        return int(vint - (vint % block_size) + jint)

    return value


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


def handle_none_content(content: _T | None, default: _T | None) -> _T | None:
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
    value: int, capabilities: type[Enum]
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


def is_enum(v: Any) -> bool:
    """Check if the value is an enum."""

    return isinstance(v, type) and issubclass(v, Enum)


def list_from_dict(raw: dict[Any, Any] | list[Any] | None) -> list[str]:
    """Return dictionary keys as list."""

    if isinstance(raw, list):
        return raw

    if not isinstance(raw, dict):
        return []

    return list(raw.keys())


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


def run_method(
    value: Any, method: Callable[..., Any] | list[Callable[..., Any]] | None
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
def safe_bool(content: str | float | bool | None) -> bool | None:
    """Read the content as boolean or return None."""

    if content is None:
        return None

    if isinstance(content, bool):
        return content
    if isinstance(content, int | float):
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
    content: str | float | None,
    default: _T | None = None,
    fallback_func: Callable[[Any], _T] | None = None,
) -> _T | None:
    """Try to convert the content using the conversion function.

    Return the default value if it fails.
    """

    if content is None:
        return default
    try:
        return convert_func(content)
    except (ValueError, TypeError):
        if fallback_func is not None and isinstance(content, str):
            try:
                return fallback_func(content)
            except (ValueError, TypeError):
                pass
        return default


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


@clean_input
def safe_exists(content: str | None) -> bool:
    """Read the content as boolean or return None."""

    return content is not None


@clean_input
def safe_float(
    content: str | float | None, default: float | None = None
) -> float | None:
    """Read the content as float or return None."""

    content = cast(
        str | int | float | None, handle_none_content(content, default)
    )
    return safe_convert(float, content, default)


@clean_input
def safe_int(
    content: str | float | None,
    default: int | None = None,
    base: int = 10,
) -> int | None:
    """Read the content as int or return the default value.

    (None if not specified).
    """

    content = cast(
        str | int | float | None, handle_none_content(content, default)
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


def safe_list_csv(content: str | None) -> list[str]:
    """Read the list as comma separated values."""

    return safe_list_from_string(content, ",")


@clean_input
def safe_list_from_string(
    content: str | None, delimiter: str = " "
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


def safe_time_from_delta(content: str) -> datetime:
    """Transform time delta to the date in the past."""

    return datetime.now(UTC).replace(
        microsecond=0, tzinfo=UTC
    ) - safe_timedelta_long(content)


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


def safe_unpack_key(
    content: tuple[str, Callable[..., Any] | None | list[Callable[..., Any]]]
    | str
    | tuple[str],
) -> tuple[str, Callable[..., Any] | list[Callable[..., Any]] | None]:
    """
    Unpacks a tuple containing a key and a method.

    The input can be a tuple of a string and a method, a single string,
    or a single-item tuple with a string.
    If the input is a string or a single-item tuple, the returned method
    is None.
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


def safe_unpack_keys(
    content: tuple[
        str, str, Callable[..., Any] | None | list[Callable[..., Any]]
    ]
    | tuple[str, str]
    | str,
) -> tuple[Any, ...]:
    """Unpack key/key_to_use/method tuple even if some values are missing."""

    if isinstance(content, tuple):
        # All 3 values are present
        if len(content) == 3:  # noqa: PLR2004
            return content

        # No method selected
        if len(content) == 2:  # noqa: PLR2004
            return content + (None,)

    # No method and key_to_use selected
    # We need to replace key_to_use with key
    new_content = (content, content)
    return new_content + (None,)


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


def safe_timestamp_to_utc(value: int | None) -> datetime | None:
    """Convert timestamp to UTC datetime."""

    if value is None:
        return None

    try:
        return datetime.fromtimestamp(value, UTC)
    except (ValueError, TypeError, OSError):
        try:
            return datetime.fromtimestamp(value / 1000, UTC)
        except (ValueError, TypeError, OSError):
            return None


def safe_utc_to_timestamp(value: datetime | None) -> float | None:
    """Convert UTC datetime to timestamp."""

    if value is None or not isinstance(value, datetime):
        return None

    return value.timestamp()


def safe_utc_to_timestamp_milli(value: datetime | None) -> int | None:
    """Convert UTC datetime to timestamp in milliseconds."""

    _timestamp = safe_utc_to_timestamp(value)

    if _timestamp is None:
        return None

    return int(_timestamp * 1000)


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
