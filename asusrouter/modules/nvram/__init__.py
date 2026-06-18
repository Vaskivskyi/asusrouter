"""NVRAM module for AsusRouter.

This module is for NVRAM-related operations.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from asusrouter.const import (
    AR_CALL_GET_STATE,
    AR_CALL_TRANSLATE_STATE,
    UNKNOWN_MEMBER_STR,
)
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.source import ARDataType
from asusrouter.registry import (
    ARCallableEntry,
    ARCallableRegistry as ARCallReg,
)
from asusrouter.tools.converters import safe_enum
from asusrouter.tools.identifiers import MacAddress
from asusrouter.tools.types import ARCallableType, ARCallbackType
from asusrouter.tools.writers import nvram

read_mac = MacAddress.from_value_safe


class ARNvramType(ARDataType):
    """AsusRouter NVRAM type class."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    # Device information
    MAC = "label_mac"
    MODEL = "productid"
    MODEL_ORIGINAL = "odmpid"
    SECRET_CODE = "secret_code"  # noqa: S105
    SERIAL = "serial_no"
    WIRELESS_BANDS = "wlnband_list"

    # Brand and geographical information
    COBRAND = "CoBrand"
    GEO_LOCATION = "location_code"
    GEO_TERRITORY = "territory_code"

    # Firmware information (can change)
    FW_MAJOR = "firmver"
    FW_MINOR = "buildno"
    FW_BUILD = "extendno"
    FW_SWPJ = "swpjverno"

    # Hardware information (cannot change)
    HW_ID = "HwId"

    # Software information (configurable by user)
    SW_MODE = "sw_mode"

    # Everything further is grouped by category
    # Categories go in alphabetical order, same for items in item

    # AI Board
    AI_FW_PATH = "ai_fw_path"
    AI_RESCUE_TIME = "ai_rescue_ts"
    AI_STATUS = "ai_prog_status"

    # DDNS
    DDNS_STATE = "ddns_enable_x"
    DDNS_SERVER = "ddns_server_x"
    DDNS_HOSTNAME = "ddns_hostname_x"
    DDNS_OLD_NAME = "ddns_old_name"
    DDNS_UPDATED = "ddns_updated"
    DDNS_RETURN_CODE_CHK = "ddns_return_code_chk"

    # DNS
    DNS_PING_STATUS = "dns_ping_state"

    # Dual WAN
    DUAL_WAN_CONFIG = "wans_dualwan"
    DUAL_WAN_MODE = "wans_mode"

    # DWB
    DWB_BAND = "dwb_band"
    DWB_MODE = "dwb_mode"

    # EULA
    EULA_STATE = "ASUS_NEW_EULA"
    EULA_TIME = "ASUS_NEW_EULA_time"
    EULA_OLD_TIME = "TM_EULA_time"
    EULA_OLD_STATE = "TM_EULA"

    # FTP
    FTP_MODE = "st_ftp_mode"
    FTP_STATE = "enable_ftp"

    # HTTP
    HTTP_AUTOLOGOUT = "http_autologout"  # minutes
    HTTP_PREFERRED_LANGUAGE = "preferred_lang"

    # IP
    IP_LAN = "lan_ipaddr"
    IP_LAN_T = "lan_ipaddr_t"

    # LED
    AURA = "AllLED"
    AURA_NIGHT_MODE = "ledg_night_mode"
    AURA_SCHEME = "ledg_scheme"
    AURA_SCHEME_PREV = "ledg_scheme_old"
    LED = "led_val"

    # Let's Encrypt
    LETS_ENCRYPT_STATE = "le_enable"
    LETS_ENCRYPT_STATUS = "le_state"

    # MAC addresses
    MAC_LAN = "lan_hwaddr"
    MAC_WAN = "wan_hwaddr"

    # Samba
    SAMBA_MODE = "st_samba_mode"
    SAMBA_STATE = "enable_samba"

    # WAN
    WAN_PROTOCOL = "wan_proto"

    # WPS
    WPS_STATE = "wps_enable"


_TRANSLATION_TABLE: dict[ARNvramType, ARCallableType] = {
    ARNvramType.MAC: read_mac,
    # MAC addresses
    ARNvramType.MAC_LAN: read_mac,
    ARNvramType.MAC_WAN: read_mac,
}


async def get_state(
    callback: ARCallbackType,
    source: ARNvramType | Iterable[ARNvramType],
    **kwargs: Any,
) -> dict[ARNvramType, str]:
    """Fetch the NVRAM data state."""

    endpoint = AREndpoint.FETCH_DATA
    request = "hook=" + nvram(
        [source] if isinstance(source, ARNvramType) else list(source),
    )

    response = await callback(endpoint=endpoint, request=request)

    if not isinstance(response, dict):
        return {}

    return {
        k: v
        for key, v in response.items()
        if (k := safe_enum(ARNvramType, key)) is not None
        and k is not ARNvramType.UNKNOWN
    }


def translate_state(
    data: dict[ARNvramType, Any],
    **kwargs: Any,
) -> dict[ARNvramType, Any]:
    """Translate the NVRAM data state."""

    return {
        k: (_TRANSLATION_TABLE[k](v) if k in _TRANSLATION_TABLE else v)
        for k, v in data.items()
    }


calls: dict[str, ARCallableEntry] = {
    AR_CALL_GET_STATE: (get_state, True),
    AR_CALL_TRANSLATE_STATE: (translate_state, True),
}

ARCallReg.register(ARNvramType, **calls)
