"""Supported AI."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.ai import ARAICapability
from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.helpers import make_bool_translator
from asusrouter.tools.readers import is_true_in_dict

translate_ai = make_bool_translator(ARSupportValue.AI.value)


def translate_ai_capabilities(data: dict[str, Any]) -> list[ARAICapability]:
    """Translate AI capabilities support data."""

    if not isinstance(data, dict):
        return []  # type: ignore[unreachable]

    result: list[ARAICapability] = []

    if is_true_in_dict(ARSupportValue.AI_SLM.value, data):
        result.append(ARAICapability.SLM)

    if is_true_in_dict(ARSupportValue.AI_UPGRADE_BETA.value, data):
        result.append(ARAICapability.UPGRADE_BETA)

    if is_true_in_dict(ARSupportValue.AI_RESET_BETA.value, data):
        result.append(ARAICapability.RESET_BETA)

    return result
