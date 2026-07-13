"""NVRAM data source for AsusRouter."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from asusrouter.modules.common.connection import (
    ARConnectionMethod,
    ARConnectionStatus,
)
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.endpoint_v2.hooks import ARHook, hook_request
from asusrouter.modules.nvram.enums import ARNvramIndexType, ARNvramType
from asusrouter.modules.source import ARDataSource
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.converters import safe_list_from_string
from asusrouter.tools.converters_v2.raw import raw_to_bool, raw_to_int
from asusrouter.tools.identifiers import MacAddress
from asusrouter.tools.identifiers.ip import IpAddress, read_ip_list
from asusrouter.tools.types import ARCallableType, ARCallbackType

read_mac = MacAddress.from_value_safe


class ARNvramIndexSource(ARDataSource):
    """An `ARNvramIndexType` bound to an index, fetchable as one NVRAM key.

    The index is usually an int unit; string indices serve composite
    prefixes (e.g. a band `2g1`, a guest slot `0.1`, an AP group `g1`).
    """

    def __init__(self, kind: ARNvramIndexType, index: int | str) -> None:
        """Initialize the indexed NVRAM source."""

        super().__init__()

        self.kind = kind
        self.index = index

    @property
    def key(self) -> str:
        """The resolved NVRAM key (e.g. `wan0_ipaddr`)."""

        return self.kind.key(self.index)

    def as_hook(self) -> tuple[ARHook, str]:
        """Render as an `nvram_get` hook call."""

        return (ARHook.NVRAM_GET, self.key)

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
    # WAN globals
    ARNvramType.DUAL_WAN_CAPABILITY: safe_list_from_string,
    ARNvramType.DUAL_WAN_CONFIG: safe_list_from_string,
    ARNvramType.DUAL_WAN_EXTWAN: raw_to_bool,
    ARNvramType.DUAL_WAN_LANPORT: raw_to_int,
    ARNvramType.DUAL_WAN_ROUTING: raw_to_bool,
    ARNvramType.DUAL_WAN_STANDBY: raw_to_bool,
    ARNvramType.DUAL_WAN_USB_BACKUP: raw_to_bool,
    ARNvramType.LINK_INTERNET: ARConnectionStatus.from_value,
    ARNvramType.LINK_WAN0: raw_to_bool,
    ARNvramType.LINK_WAN1: raw_to_bool,
    ARNvramType.WAN_AGGREGATION: raw_to_bool,
    ARNvramType.WAN_AGGREGATION_PORTS: safe_list_from_string,
    ARNvramType.WAN_AUTODETECT: raw_to_bool,
    ARNvramType.WAN_S46_AFTR: IpAddress.from_value_safe,
    ARNvramType.WAN_S46_B4ADDR: IpAddress.from_value_safe,
    ARNvramType.WAN_UNIT: raw_to_int,
    ARNvramType.WATCHDOG_ENABLE: raw_to_bool,
    ARNvramType.WATCHDOG_FAILBACK_COUNT: raw_to_int,
    ARNvramType.WATCHDOG_INTERVAL: raw_to_int,
    ARNvramType.WATCHDOG_MAX_FAIL: raw_to_int,
    # WAN per-unit status
    ARNvramIndexType.WAN_DOT1Q: raw_to_bool,
    ARNvramIndexType.WAN_ENABLE: raw_to_bool,
    ARNvramIndexType.WAN_PRIMARY: raw_to_bool,
    ARNvramIndexType.WAN_PROTO: ARConnectionMethod.from_value,
    ARNvramIndexType.WAN_REALIP: IpAddress.from_value_safe,
    ARNvramIndexType.WAN_REALIP_STATE: raw_to_bool,
    ARNvramIndexType.WAN_STATE: ARConnectionStatus.from_value,
    ARNvramIndexType.WAN_STATE_AUX: ARConnectionStatus.from_value,
    ARNvramIndexType.WAN_STATE_SUB: ARConnectionStatus.from_value,
    ARNvramIndexType.WAN_VID: raw_to_int,
    # WAN per-unit addresses
    ARNvramIndexType.WAN_DNS: read_ip_list,
    ARNvramIndexType.WAN_DNS_X: read_ip_list,
    ARNvramIndexType.WAN_EXPIRES: raw_to_int,
    ARNvramIndexType.WAN_EXPIRES_X: raw_to_int,
    ARNvramIndexType.WAN_GATEWAY: IpAddress.from_value_safe,
    ARNvramIndexType.WAN_GATEWAY_X: IpAddress.from_value_safe,
    ARNvramIndexType.WAN_IPADDR: IpAddress.from_value_safe,
    ARNvramIndexType.WAN_IPADDR_X: IpAddress.from_value_safe,
    ARNvramIndexType.WAN_LEASE: raw_to_int,
    ARNvramIndexType.WAN_LEASE_X: raw_to_int,
    ARNvramIndexType.WAN_NETMASK: IpAddress.from_value_safe,
    ARNvramIndexType.WAN_NETMASK_X: IpAddress.from_value_safe,
    # WAN per-unit connection config
    ARNvramIndexType.WAN_DHCP_ENABLE: raw_to_bool,
    ARNvramIndexType.WAN_DNS1: IpAddress.from_value_safe,
    ARNvramIndexType.WAN_DNS2: IpAddress.from_value_safe,
    ARNvramIndexType.WAN_DNS_ENABLE: raw_to_bool,
    ARNvramIndexType.WAN_MAC_CLONE: read_mac,
    ARNvramIndexType.WAN_MTU: raw_to_int,
    ARNvramIndexType.WAN_NAT: raw_to_bool,
    ARNvramIndexType.WAN_ROUTING_ISP_ENABLE: raw_to_bool,
    # WAN per-unit PPP
    ARNvramIndexType.WAN_PPPOE_IDLETIME: raw_to_int,
    ARNvramIndexType.WAN_PPPOE_MRU: raw_to_int,
    ARNvramIndexType.WAN_PPPOE_MTU: raw_to_int,
    ARNvramIndexType.WAN_PPP_ECHO: raw_to_int,
    ARNvramIndexType.WAN_PPP_ECHO_FAILURE: raw_to_int,
    ARNvramIndexType.WAN_PPP_ECHO_INTERVAL: raw_to_int,
    # WAN per-unit softwire
    ARNvramIndexType.WAN_S46_DSLITE_MODE: raw_to_int,
    ARNvramIndexType.WAN_S46_EALEN: raw_to_int,
    ARNvramIndexType.WAN_S46_OFFSET: raw_to_int,
    ARNvramIndexType.WAN_S46_PEER: IpAddress.from_value_safe,
    ARNvramIndexType.WAN_S46_PREFIX4: IpAddress.from_value_safe,
    ARNvramIndexType.WAN_S46_PREFIX4LEN: raw_to_int,
    ARNvramIndexType.WAN_S46_PREFIX6: IpAddress.from_value_safe,
    ARNvramIndexType.WAN_S46_PREFIX6LEN: raw_to_int,
    ARNvramIndexType.WAN_S46_PSID: raw_to_int,
    ARNvramIndexType.WAN_S46_PSIDLEN: raw_to_int,
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

    request = hook_request(*forward.values())
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


ARCallReg.register_module(
    ARNvramType,
    get_state=get_state,
    translate_state=translate_state,
    multi=True,
)
ARCallReg.register_module(
    ARNvramIndexSource,
    get_state=get_state,
    translate_state=translate_state,
    multi=True,
)
