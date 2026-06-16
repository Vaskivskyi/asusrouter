"""Supported LAN."""

from __future__ import annotations

from asusrouter.modules.lan import ARLANCapability
from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.helpers import make_list_translator

translate_lan_capabilities = make_list_translator(
    {
        ARSupportValue.LAN_AGGREGATION.value: ARLANCapability.AGGREGATION,
    }
)
