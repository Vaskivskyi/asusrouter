"""Supported AI."""

from __future__ import annotations

from asusrouter.modules.ai import ARAICapability
from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.helpers import (
    make_bool_translator,
    make_list_translator,
)

translate_ai = make_bool_translator(ARSupportValue.AI.value)
translate_ai_capabilities = make_list_translator(
    {
        ARSupportValue.AI_SLM.value: ARAICapability.SLM,
        ARSupportValue.AI_UPGRADE_BETA.value: ARAICapability.UPGRADE_BETA,
        ARSupportValue.AI_RESET_BETA.value: ARAICapability.RESET_BETA,
    }
)
