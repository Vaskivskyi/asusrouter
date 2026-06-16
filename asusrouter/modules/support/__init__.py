"""Support module for AsusRouter.

This module is for services support by devices.
"""

from __future__ import annotations

from typing import Any

from asusrouter.const import AR_CALL_GET_STATE, AR_CALL_TRANSLATE_STATE
from asusrouter.modules.endpoint import Endpoint
from asusrouter.modules.source import ARDataSource
from asusrouter.modules.support.ai import (
    translate_ai,
    translate_ai_capabilities,
)
from asusrouter.modules.support.aimesh import (
    translate_aimesh,
    translate_aimesh_capabilities,
    translate_aimesh_generation,
)
from asusrouter.modules.support.aura import (
    translate_aura,
    translate_aura_night_mode,
    translate_aura_zone,
)
from asusrouter.modules.support.connection import translate_connection
from asusrouter.modules.support.dsl import translate_dsl
from asusrouter.modules.support.flag import ARSupportType
from asusrouter.modules.support.ftp import (
    translate_ftp,
    translate_ftp_capabilities,
)
from asusrouter.modules.support.lan import translate_lan_capabilities
from asusrouter.modules.support.platform import translate_platform
from asusrouter.modules.support.speedtest import (
    translate_speedtest,
    translate_speedtest_capabilities,
)
from asusrouter.modules.support.usb import (
    translate_usb_generation,
    translate_usb_ports,
    translate_usb_wan,
)
from asusrouter.modules.support.wan import (
    translate_wan,
    translate_wan_capabilities,
    translate_wan_limit,
)
from asusrouter.modules.support.wifi import (
    translate_wifi_generation,
    translate_wifi_multiband,
    translate_wifi_units,
)
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.types import ARCallableType, ARCallbackType


class ARSupportSource(ARDataSource):
    """AsusRouter support data source."""

    def __init__(self) -> None:
        """Initialize the support data source."""

        super().__init__()


# Universal instance - preferred
ARSupportSourceUniversal: ARSupportSource = ARSupportSource()


TRANSLATION_TABLE: dict[ARSupportType, ARCallableType] = {
    ARSupportType.AI: translate_ai,
    ARSupportType.AI_CAPABILITIES: translate_ai_capabilities,
    ARSupportType.AIMESH: translate_aimesh,
    ARSupportType.AIMESH_CAPABILITIES: translate_aimesh_capabilities,
    ARSupportType.AIMESH_GENERATION: translate_aimesh_generation,
    ARSupportType.AURA: translate_aura,
    ARSupportType.AURA_NIGHT_MODE: translate_aura_night_mode,
    ARSupportType.AURA_ZONE: translate_aura_zone,
    ARSupportType.CONNECTIONS: translate_connection,
    ARSupportType.DSL: translate_dsl,
    ARSupportType.FTP: translate_ftp,
    ARSupportType.FTP_CAPABILITIES: translate_ftp_capabilities,
    ARSupportType.LAN_CAPABILITIES: translate_lan_capabilities,
    ARSupportType.PLATFORM: translate_platform,
    ARSupportType.SPEEDTEST: translate_speedtest,
    ARSupportType.SPEEDTEST_CAPABILITIES: translate_speedtest_capabilities,
    ARSupportType.USB_GENERATION: translate_usb_generation,
    ARSupportType.USB_PORTS: translate_usb_ports,
    ARSupportType.USB_WAN: translate_usb_wan,
    ARSupportType.WAN: translate_wan,
    ARSupportType.WAN_CAPABILITIES: translate_wan_capabilities,
    ARSupportType.WAN_LIMIT: translate_wan_limit,
    ARSupportType.WIFI_GENERATION: translate_wifi_generation,
    ARSupportType.WIFI_MULTIBAND: translate_wifi_multiband,
    ARSupportType.WIFI_UNITS: translate_wifi_units,
}


async def get_state(
    callback: ARCallbackType,
    source: ARSupportSource,
    **kwargs: Any,
) -> dict[str, Any]:
    """Fetch the support data state."""

    endpoint = Endpoint.HOOK
    request = "hook=get_ui_support()"

    response = await callback(endpoint=endpoint, request=request)

    if isinstance(response, dict):
        ui_support = response.get("get_ui_support")
        if isinstance(ui_support, dict):
            return ui_support

    return {}


def translate_state(
    data: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    """Translate the support data to a simple format."""

    result: dict[str, Any] = {}

    for support_type, interpreter in TRANSLATION_TABLE.items():
        result[support_type] = interpreter(data)

    return result


calls: dict[str, ARCallableType] = {
    AR_CALL_GET_STATE: get_state,
    AR_CALL_TRANSLATE_STATE: translate_state,
}

ARCallReg.register(ARSupportSource, **calls)
