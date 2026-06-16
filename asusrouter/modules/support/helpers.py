"""Helper for the support module."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from asusrouter.modules.support.flag import ARSupportType
from asusrouter.tools.converters import safe_int_nn
from asusrouter.tools.readers import is_true_in_dict

_T = TypeVar("_T")


def make_bool_translator(
    key: str, *, negate: bool = False
) -> Callable[[dict[str, Any]], bool]:
    """Create a bool translator for the given support key."""

    def translate(data: dict[str, Any]) -> bool:
        if not isinstance(data, dict):
            return False  # type: ignore[unreachable]
        result = is_true_in_dict(key, data)
        return not result if negate else result

    return translate


def make_enum_translator(
    table: dict[str, _T], default: _T
) -> Callable[[dict[str, Any]], _T]:
    """Create a translator returning the first matching value or default."""

    def translate(data: dict[str, Any]) -> _T:
        if not isinstance(data, dict):
            return default  # type: ignore[unreachable]
        for key, value in table.items():
            if is_true_in_dict(key, data):
                return value
        return default

    return translate


def make_int_translator(key: str) -> Callable[[dict[str, Any]], int]:
    """Create an int translator for the given support key."""

    def translate(data: dict[str, Any]) -> int:
        if not isinstance(data, dict):
            return 0  # type: ignore[unreachable]
        return safe_int_nn(data.get(key))

    return translate


def make_list_translator(
    table: dict[str, _T],
) -> Callable[[dict[str, Any]], list[_T]]:
    """Create a list translator for the given support value table."""

    def translate(data: dict[str, Any]) -> list[_T]:
        if not isinstance(data, dict):
            return []  # type: ignore[unreachable]
        return [
            value for key, value in table.items() if is_true_in_dict(key, data)
        ]

    return translate


def support_available(
    support: dict[ARSupportType, Any], key: ARSupportType
) -> bool:
    """Return True if the bool support flag is set."""

    return support.get(key) is True


def support_available_in(
    support: dict[ARSupportType, Any], key: ARSupportType, item: Any
) -> bool:
    """Return True if item is present in the list under the given key."""

    value = support.get(key)
    return isinstance(value, list) and item in value


def support_value(
    support: dict[ARSupportType, Any], key: ARSupportType
) -> Any:
    """Return the support value for the given key."""

    return support.get(key)
