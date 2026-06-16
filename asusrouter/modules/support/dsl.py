"""Supported DSL."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.tools.readers import is_true_in_dict


def translate_dsl(data: dict[str, Any]) -> bool:
    """Translate DSL support data."""

    if not isinstance(data, dict):
        return False  # type: ignore[unreachable]

    return is_true_in_dict(ARSupportValue.DSL.value, data)
