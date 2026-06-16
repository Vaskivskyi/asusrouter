"""Supported WAN."""

from __future__ import annotations

from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.helpers import (
    make_bool_translator,
    make_int_translator,
    make_list_translator,
)
from asusrouter.modules.wan import ARWANCapability

translate_wan = make_bool_translator(
    ARSupportValue.WAN_NOWAN.value, negate=True
)

translate_wan_capabilities = make_list_translator(
    {
        ARSupportValue.WAN_AGGREGATION.value: ARWANCapability.AGGREGATION,
        ARSupportValue.WAN_DUALWAN.value: ARWANCapability.DUALWAN,
    }
)

translate_wan_limit = make_int_translator(ARSupportValue.WAN_LIMIT.value)
