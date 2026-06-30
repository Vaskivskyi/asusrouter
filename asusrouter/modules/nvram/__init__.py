"""NVRAM module for AsusRouter.

This module is for NVRAM-related operations.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from typing import Any

from asusrouter.const import (
    AR_CALL_GET_STATE,
    AR_CALL_TRANSLATE_STATE,
    UNKNOWN_MEMBER_STR,
)
from asusrouter.modules.common.connection import (
    ARConnectionMethod,
    ARConnectionStatus,
)
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.source import ARDataSource, ARDataType
from asusrouter.registry import (
    ARCallableEntry,
    ARCallableRegistry as ARCallReg,
)
from asusrouter.tools.converters import safe_list_from_string
from asusrouter.tools.converters_v2.raw import raw_to_bool, raw_to_int
from asusrouter.tools.enum import FromStrMixin
from asusrouter.tools.identifiers import MacAddress
from asusrouter.tools.identifiers.ip import IpAddress, read_ip_list
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
    LINK_INTERNET = "link_internet"
    LINK_WAN0 = "link_wan"
    LINK_WAN1 = "link_wan1"
    WAN_AGGREGATION = "bond_wan"
    WAN_AGGREGATION_PORTS = "wanports_bond"
    WAN_PROTOCOL = "wan_proto"

    # WPS
    WPS_STATE = "wps_enable"


class ARNvramIndexType(FromStrMixin, StrEnum):
    """Indexed NVRAM keys: each member is an f-string template (one `{}`)."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    # WAN (per-unit)
    WAN_ENABLE = "wan{}_enable"
    WAN_PRIMARY = "wan{}_primary"
    WAN_PROTO = "wan{}_proto"
    WAN_REALIP = "wan{}_realip_ip"
    WAN_REALIP_STATE = "wan{}_realip_state"
    WAN_STATE = "wan{}_state_t"
    WAN_STATE_AUX = "wan{}_auxstate_t"
    WAN_STATE_SUB = "wan{}_sbstate_t"

    # WAN address - main (`wan{n}_`)
    WAN_DNS = "wan{}_dns"
    WAN_EXPIRES = "wan{}_expires"
    WAN_GATEWAY = "wan{}_gateway"
    WAN_IPADDR = "wan{}_ipaddr"
    WAN_LEASE = "wan{}_lease"
    WAN_NETMASK = "wan{}_netmask"

    # WAN address - extra (`wan{n}x_`)
    WAN_DNS_X = "wan{}x_dns"
    WAN_EXPIRES_X = "wan{}x_expires"
    WAN_GATEWAY_X = "wan{}x_gateway"
    WAN_IPADDR_X = "wan{}x_ipaddr"
    WAN_LEASE_X = "wan{}x_lease"
    WAN_NETMASK_X = "wan{}x_netmask"


class ARNvramIndexSource(ARDataSource):
    """An `ARNvramIndexType` bound to an index, fetchable as one NVRAM key."""

    def __init__(self, kind: ARNvramIndexType, index: int) -> None:
        """Initialize the indexed NVRAM source."""

        super().__init__()

        self.kind = kind
        self.index = index

    @property
    def key(self) -> str:
        """The resolved NVRAM key (e.g. `wan0_ipaddr`)."""

        return self.kind.value.format(self.index)

    def __eq__(self, other: object) -> bool:
        """Equal by kind and index."""

        if not isinstance(other, ARNvramIndexSource):
            return NotImplemented
        return self.kind == other.kind and self.index == other.index

    def __hash__(self) -> int:
        """Hash by kind and index."""

        return hash((type(self), self.kind, self.index))

    def __repr__(self) -> str:
        """Representation of the indexed NVRAM source."""

        return f"<ARNvramIndexSource {self.key}>"


# A flat or indexed NVRAM request item
ARNvramItem = ARNvramType | ARNvramIndexSource


# Translators per member; indexed values key on their template type
# Only general (common / utility) translations belong here - module-specific
# conversions stay in their own module
# Flat and indexed keys never collide: index templates contain `{}`
_TRANSLATION: dict[ARNvramType | ARNvramIndexType, ARCallableType] = {
    ARNvramType.MAC: read_mac,
    ARNvramType.MAC_LAN: read_mac,
    ARNvramType.MAC_WAN: read_mac,
    # WAN
    ARNvramType.LINK_INTERNET: ARConnectionStatus.from_value,
    ARNvramType.LINK_WAN0: raw_to_bool,
    ARNvramType.LINK_WAN1: raw_to_bool,
    ARNvramType.WAN_AGGREGATION: raw_to_bool,
    ARNvramType.WAN_AGGREGATION_PORTS: safe_list_from_string,
    ARNvramType.DUAL_WAN_CONFIG: safe_list_from_string,
    ARNvramIndexType.WAN_ENABLE: raw_to_bool,
    ARNvramIndexType.WAN_PRIMARY: raw_to_bool,
    ARNvramIndexType.WAN_PROTO: ARConnectionMethod.from_value,
    ARNvramIndexType.WAN_STATE: ARConnectionStatus.from_value,
    ARNvramIndexType.WAN_STATE_SUB: ARConnectionStatus.from_value,
    ARNvramIndexType.WAN_STATE_AUX: ARConnectionStatus.from_value,
    ARNvramIndexType.WAN_REALIP: IpAddress.from_value_safe,
    ARNvramIndexType.WAN_REALIP_STATE: raw_to_bool,
    ARNvramIndexType.WAN_DNS: read_ip_list,
    ARNvramIndexType.WAN_DNS_X: read_ip_list,
    ARNvramIndexType.WAN_GATEWAY: IpAddress.from_value_safe,
    ARNvramIndexType.WAN_GATEWAY_X: IpAddress.from_value_safe,
    ARNvramIndexType.WAN_IPADDR: IpAddress.from_value_safe,
    ARNvramIndexType.WAN_IPADDR_X: IpAddress.from_value_safe,
    ARNvramIndexType.WAN_NETMASK: IpAddress.from_value_safe,
    ARNvramIndexType.WAN_NETMASK_X: IpAddress.from_value_safe,
    ARNvramIndexType.WAN_LEASE: raw_to_int,
    ARNvramIndexType.WAN_LEASE_X: raw_to_int,
    ARNvramIndexType.WAN_EXPIRES: raw_to_int,
    ARNvramIndexType.WAN_EXPIRES_X: raw_to_int,
}


def _resolve_key(item: ARNvramItem) -> str:
    """Resolve a requested item to its raw NVRAM key."""

    if isinstance(item, ARNvramIndexSource):
        return item.key
    return item.value


async def get_state(
    callback: ARCallbackType,
    source: ARNvramItem | Iterable[ARNvramItem],
    **kwargs: Any,
) -> dict[ARNvramItem, str]:
    """Fetch the NVRAM data state."""

    items: list[ARNvramItem] = (
        [source]
        if isinstance(source, (ARNvramType, ARNvramIndexSource))
        else list(source)
    )

    # Map each raw key back to the item that requested it
    forward: dict[str, ARNvramItem] = {
        _resolve_key(item): item for item in items
    }

    request = "hook=" + (nvram(list(forward.keys())) or "")
    response = await callback(endpoint=AREndpoint.FETCH_DATA, request=request)

    if not isinstance(response, dict):
        return {}

    return {
        requester: value
        for key, value in response.items()
        if (requester := forward.get(key)) is not None
    }


def translate_state(
    data: dict[ARNvramItem, Any],
    **kwargs: Any,
) -> dict[ARNvramItem, Any]:
    """Translate the NVRAM data state."""

    result: dict[ARNvramItem, Any] = {}
    for item, value in data.items():
        member: ARNvramType | ARNvramIndexType = (
            item.kind if isinstance(item, ARNvramIndexSource) else item
        )
        converter = _TRANSLATION.get(member)
        result[item] = converter(value) if converter else value
    return result


calls: dict[str, ARCallableEntry] = {
    AR_CALL_GET_STATE: (get_state, True),
    AR_CALL_TRANSLATE_STATE: (translate_state, True),
}

ARCallReg.register(ARNvramType, **calls)
ARCallReg.register(ARNvramIndexSource, **calls)
