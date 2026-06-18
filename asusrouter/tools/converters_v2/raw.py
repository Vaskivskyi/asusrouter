"""Raw value converters for AsusRouter."""

from __future__ import annotations

from typing import Any

_BOM = "﻿"  # This is a literal BOM character. Don't edit it!

_STR_TO_BOOL: dict[str, bool] = {
    "true": True,
    "allow": True,
    "enable": True,
    "enabled": True,
    "yes": True,
    "1": True,
    "on": True,
    "false": False,
    "block": False,
    "disable": False,
    "disabled": False,
    "no": False,
    "0": False,
    "off": False,
}


def raw_to_str(value: Any) -> str | None:
    """Convert raw value to a clean string or None."""

    if not isinstance(value, str):
        return None
    clean = value.lstrip(_BOM).strip()
    if not clean:
        return None
    return clean


def raw_to_bool(value: Any) -> bool | None:
    """Convert raw value to bool or None."""

    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return value != 0
    cleaned = raw_to_str(value)
    if cleaned is None:
        return None
    return _STR_TO_BOOL.get(cleaned.lower())


def raw_to_float(value: Any) -> float | None:
    """Convert raw value to float or None."""

    if isinstance(value, float):
        return value
    if isinstance(value, int):
        return float(value)
    cleaned = raw_to_str(value)
    if cleaned is None:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def raw_to_int(value: Any, base: int = 10) -> int | None:
    """Convert raw value to int or None."""

    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        try:
            return int(value)
        except (ValueError, OverflowError):
            return None
    cleaned = raw_to_str(value)
    if cleaned is not None:
        try:
            return int(cleaned, base)
        except ValueError:
            try:
                return int(float(cleaned))
            except (ValueError, OverflowError):
                pass
    return None
