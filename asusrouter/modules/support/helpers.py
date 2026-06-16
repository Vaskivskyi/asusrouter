"""Helper factories for support translators."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from asusrouter.tools.readers import is_true_in_dict


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
