"""Helper factories for support translators."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from asusrouter.tools.converters import safe_int_nn
from asusrouter.tools.readers import is_true_in_dict

_T = TypeVar("_T")


def make_list_translator(
    table: dict[str, _T],
) -> Callable[[dict[str, Any]], list[_T]]:
    """Create a list translator for the given support value table."""

    def translate(data: dict[str, Any]) -> list[_T]:
        if not isinstance(data, dict):
            return []  # type: ignore[unreachable]
        return [cap for sv, cap in table.items() if is_true_in_dict(sv, data)]

    return translate


def make_int_translator(key: str) -> Callable[[dict[str, Any]], int]:
    """Create an int translator for the given support key."""

    def translate(data: dict[str, Any]) -> int:
        if not isinstance(data, dict):
            return 0  # type: ignore[unreachable]
        return safe_int_nn(data.get(key))

    return translate


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
