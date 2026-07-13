"""WAN data source for AsusRouter."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from asusrouter.modules.common.connection import (
    ARConnectionMethod,
    ARConnectionStatus,
)
from asusrouter.modules.nvram import (
    ARNvramIndexSource,
    ARNvramIndexType,
    ARNvramItem,
    ARNvramType,
)
from asusrouter.modules.source import ARDataSource
from asusrouter.modules.wan.enums import ARDualWanMode
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.converters_v2.raw import raw_to_int, raw_to_str
from asusrouter.tools.identifiers import MacAddress
from asusrouter.tools.identifiers.ip import IpAddress
from asusrouter.tools.types import ARCallbackType

__all__ = [
    "ARDualWan",
    "ARWan",
    "ARWanAddress",
    "ARWanAggregation",
    "ARWanPPP",
    "ARWanSoftwire",
    "ARWanSource",
    "ARWanSourceUniversal",
    "ARWanUnit",
    "ARWanVlan",
    "ARWanWatchdog",
    "get_state",
    "translate_state",
]


# Units fetched for WAN (primary and secondary)
_WAN_UNITS = (0, 1)


@dataclass
class ARWanAddress:
    """A WAN address block (the runtime `main` or configured `extra` set)."""

    ip: IpAddress | None = None
    gateway: IpAddress | None = None
    mask: IpAddress | None = None
    dns: list[IpAddress] = field(default_factory=list)
    lease: int | None = None
    expires: int | None = None


@dataclass
class ARWanVlan:
    """WAN VLAN tagging configuration."""

    tagged: bool = False
    vid: int | None = None


@dataclass
class ARWanPPP:
    """WAN PPP / PPPoE configuration."""

    echo: int | None = None
    echo_interval: int | None = None
    echo_failure: int | None = None
    conn: str | None = None
    heartbeat: str | None = None
    pppoe_ac: str | None = None
    pppoe_hostuniq: str | None = None
    pppoe_idletime: int | None = None
    pppoe_mru: int | None = None
    pppoe_mtu: int | None = None
    pppoe_options: str | None = None
    pppoe_service: str | None = None


@dataclass
class ARWanSoftwire:
    """WAN Softwire46 (IPv4-over-IPv6 transition) configuration."""

    dslite_mode: int | None = None
    dslite_service: str | None = None
    aftr: IpAddress | None = None
    b4addr: IpAddress | None = None
    peer: IpAddress | None = None
    prefix4: IpAddress | None = None
    prefix4_len: int | None = None
    prefix6: IpAddress | None = None
    prefix6_len: int | None = None
    ea_len: int | None = None
    offset: int | None = None
    psid: int | None = None
    psid_len: int | None = None


@dataclass
class ARWanUnit:
    """A single WAN unit (runtime status and configuration)."""

    index: int
    enable: bool = False
    primary: bool = False
    protocol: ARConnectionMethod = ARConnectionMethod.UNKNOWN
    status: ARConnectionStatus = ARConnectionStatus.UNKNOWN
    status_sub: ARConnectionStatus = ARConnectionStatus.UNKNOWN
    status_aux: ARConnectionStatus = ARConnectionStatus.UNKNOWN
    link: bool = False
    real_ip: IpAddress | None = None
    real_ip_state: bool = False
    main: ARWanAddress = field(default_factory=ARWanAddress)
    extra: ARWanAddress = field(default_factory=ARWanAddress)

    # Configuration
    mtu: int | None = None
    nat: bool = False
    dhcp_enable: bool = False
    dns_auto: bool = False
    dns_servers: list[IpAddress] = field(default_factory=list)
    hostname: str | None = None
    client_id: str | None = None
    vendor_id: str | None = None
    mac_clone: MacAddress | None = None
    vlan: ARWanVlan = field(default_factory=ARWanVlan)
    ppp: ARWanPPP = field(default_factory=ARWanPPP)
    softwire: ARWanSoftwire = field(default_factory=ARWanSoftwire)
    routing_isp: str | None = None
    routing_isp_enable: bool = False
    isp_country: str | None = None
    isp_list: str | None = None
    isp_num: str | None = None


@dataclass
class ARDualWan:
    """Dual WAN configuration."""

    mode: ARDualWanMode = ARDualWanMode.UNKNOWN
    priority: list[str] = field(default_factory=list)
    state: bool = False
    capability: list[str] = field(default_factory=list)
    lan_port: int | None = None
    lb_ratio: tuple[int, int] | None = None
    standby: bool = False
    routing: bool = False
    usb_backup: bool = False
    autodetect: bool = False
    extwan: bool = False


@dataclass
class ARWanAggregation:
    """WAN link aggregation configuration."""

    state: bool = False
    ports: list[str] = field(default_factory=list)


@dataclass
class ARWanWatchdog:
    """WAN failover watchdog configuration."""

    enable: bool = False
    target: str | None = None
    interval: int | None = None
    max_fail: int | None = None
    failback_count: int | None = None


@dataclass
class ARWan:
    """The WAN state of the router."""

    active_unit: int | None = None
    units: dict[int, ARWanUnit] = field(default_factory=dict)
    dualwan: ARDualWan | None = None
    aggregation: ARWanAggregation | None = None
    watchdog: ARWanWatchdog | None = None
    internet_status: ARConnectionStatus = ARConnectionStatus.UNKNOWN


# Flat (global) NVRAM members for the WAN state
_WAN_FLAT: tuple[ARNvramType, ...] = (
    ARNvramType.DUAL_WAN_CAPABILITY,
    ARNvramType.DUAL_WAN_CONFIG,
    ARNvramType.DUAL_WAN_EXTWAN,
    ARNvramType.DUAL_WAN_LANPORT,
    ARNvramType.DUAL_WAN_LB_RATIO,
    ARNvramType.DUAL_WAN_MODE,
    ARNvramType.DUAL_WAN_ROUTING,
    ARNvramType.DUAL_WAN_STANDBY,
    ARNvramType.DUAL_WAN_USB_BACKUP,
    ARNvramType.LINK_INTERNET,
    ARNvramType.LINK_WAN0,
    ARNvramType.LINK_WAN1,
    ARNvramType.WAN_AGGREGATION,
    ARNvramType.WAN_AGGREGATION_PORTS,
    ARNvramType.WAN_AUTODETECT,
    ARNvramType.WAN_S46_AFTR,
    ARNvramType.WAN_S46_B4ADDR,
    ARNvramType.WAN_UNIT,
    ARNvramType.WATCHDOG_ENABLE,
    ARNvramType.WATCHDOG_FAILBACK_COUNT,
    ARNvramType.WATCHDOG_INTERVAL,
    ARNvramType.WATCHDOG_MAX_FAIL,
    ARNvramType.WATCHDOG_TARGET,
)

# Indexed (per-unit) NVRAM members for the WAN state
_WAN_INDEXED: tuple[ARNvramIndexType, ...] = (
    # Status
    ARNvramIndexType.WAN_DOT1Q,
    ARNvramIndexType.WAN_ENABLE,
    ARNvramIndexType.WAN_PRIMARY,
    ARNvramIndexType.WAN_PROTO,
    ARNvramIndexType.WAN_REALIP,
    ARNvramIndexType.WAN_REALIP_STATE,
    ARNvramIndexType.WAN_STATE,
    ARNvramIndexType.WAN_STATE_AUX,
    ARNvramIndexType.WAN_STATE_SUB,
    ARNvramIndexType.WAN_VID,
    # Addresses
    ARNvramIndexType.WAN_DNS,
    ARNvramIndexType.WAN_DNS_X,
    ARNvramIndexType.WAN_EXPIRES,
    ARNvramIndexType.WAN_EXPIRES_X,
    ARNvramIndexType.WAN_GATEWAY,
    ARNvramIndexType.WAN_GATEWAY_X,
    ARNvramIndexType.WAN_IPADDR,
    ARNvramIndexType.WAN_IPADDR_X,
    ARNvramIndexType.WAN_LEASE,
    ARNvramIndexType.WAN_LEASE_X,
    ARNvramIndexType.WAN_NETMASK,
    ARNvramIndexType.WAN_NETMASK_X,
    # Connection config
    ARNvramIndexType.WAN_CLIENTID,
    ARNvramIndexType.WAN_DHCP_ENABLE,
    ARNvramIndexType.WAN_DNS1,
    ARNvramIndexType.WAN_DNS2,
    ARNvramIndexType.WAN_DNS_ENABLE,
    ARNvramIndexType.WAN_HOSTNAME,
    ARNvramIndexType.WAN_MAC_CLONE,
    ARNvramIndexType.WAN_MTU,
    ARNvramIndexType.WAN_NAT,
    ARNvramIndexType.WAN_VENDORID,
    # ISP routing
    ARNvramIndexType.WAN_ISP_COUNTRY,
    ARNvramIndexType.WAN_ISP_LIST,
    ARNvramIndexType.WAN_ISP_NUM,
    ARNvramIndexType.WAN_ROUTING_ISP,
    ARNvramIndexType.WAN_ROUTING_ISP_ENABLE,
    # PPP
    ARNvramIndexType.WAN_HEARTBEAT,
    ARNvramIndexType.WAN_PPPOE_AC,
    ARNvramIndexType.WAN_PPPOE_HOSTUNIQ,
    ARNvramIndexType.WAN_PPPOE_IDLETIME,
    ARNvramIndexType.WAN_PPPOE_MRU,
    ARNvramIndexType.WAN_PPPOE_MTU,
    ARNvramIndexType.WAN_PPPOE_OPTIONS,
    ARNvramIndexType.WAN_PPPOE_SERVICE,
    ARNvramIndexType.WAN_PPP_CONN,
    ARNvramIndexType.WAN_PPP_ECHO,
    ARNvramIndexType.WAN_PPP_ECHO_FAILURE,
    ARNvramIndexType.WAN_PPP_ECHO_INTERVAL,
    # Softwire
    ARNvramIndexType.WAN_S46_DSLITE_MODE,
    ARNvramIndexType.WAN_S46_DSLITE_SVC,
    ARNvramIndexType.WAN_S46_EALEN,
    ARNvramIndexType.WAN_S46_OFFSET,
    ARNvramIndexType.WAN_S46_PEER,
    ARNvramIndexType.WAN_S46_PREFIX4,
    ARNvramIndexType.WAN_S46_PREFIX4LEN,
    ARNvramIndexType.WAN_S46_PREFIX6,
    ARNvramIndexType.WAN_S46_PREFIX6LEN,
    ARNvramIndexType.WAN_S46_PSID,
    ARNvramIndexType.WAN_S46_PSIDLEN,
)


# Full NVRAM request for the WAN state, built once
_WAN_REQUEST: tuple[ARNvramItem, ...] = (
    *_WAN_FLAT,
    *(
        ARNvramIndexSource(kind, index)
        for index in _WAN_UNITS
        for kind in _WAN_INDEXED
    ),
)


class ARWanSource(ARDataSource):
    """WAN data source for the connected router."""


# Universal instance - preferred
ARWanSourceUniversal: ARWanSource = ARWanSource()


_Indexed = dict[tuple[ARNvramIndexType, int | str], Any]

# Per-unit address members, ordered as the `ARWanAddress` fields use them
_ADDR_MAIN: tuple[ARNvramIndexType, ...] = (
    ARNvramIndexType.WAN_DNS,
    ARNvramIndexType.WAN_EXPIRES,
    ARNvramIndexType.WAN_GATEWAY,
    ARNvramIndexType.WAN_IPADDR,
    ARNvramIndexType.WAN_LEASE,
    ARNvramIndexType.WAN_NETMASK,
)
_ADDR_EXTRA: tuple[ARNvramIndexType, ...] = (
    ARNvramIndexType.WAN_DNS_X,
    ARNvramIndexType.WAN_EXPIRES_X,
    ARNvramIndexType.WAN_GATEWAY_X,
    ARNvramIndexType.WAN_IPADDR_X,
    ARNvramIndexType.WAN_LEASE_X,
    ARNvramIndexType.WAN_NETMASK_X,
)


def _idx(
    indexed: _Indexed,
    kind: ARNvramIndexType,
    index: int,
    default: Any = None,
) -> Any:
    """Look up a translated indexed value, or `default` if absent."""

    value = indexed.get((kind, index))
    return default if value is None else value


def _parse_lb_ratio(raw: Any) -> tuple[int, int] | None:
    """Parse a `primary:secondary` load-balance ratio into two ints."""

    text = raw_to_str(raw)
    if not text:
        return None
    try:
        primary_raw, secondary_raw = text.split(":")
    except ValueError:
        return None
    primary, secondary = raw_to_int(primary_raw), raw_to_int(secondary_raw)
    if primary is None or secondary is None:
        return None
    return (primary, secondary)


def _build_address(
    indexed: _Indexed, index: int, *, extra: bool
) -> ARWanAddress:
    """Build a WAN address block for a unit (main or extra set)."""

    dns, expires, gateway, ipaddr, lease, netmask = (
        _ADDR_EXTRA if extra else _ADDR_MAIN
    )

    return ARWanAddress(
        ip=_idx(indexed, ipaddr, index),
        gateway=_idx(indexed, gateway, index),
        mask=_idx(indexed, netmask, index),
        dns=_idx(indexed, dns, index, []),
        lease=_idx(indexed, lease, index),
        expires=_idx(indexed, expires, index),
    )


def _build_vlan(indexed: _Indexed, index: int) -> ARWanVlan:
    """Build the VLAN config for a unit."""

    return ARWanVlan(
        tagged=bool(_idx(indexed, ARNvramIndexType.WAN_DOT1Q, index)),
        vid=_idx(indexed, ARNvramIndexType.WAN_VID, index),
    )


def _build_ppp(indexed: _Indexed, index: int) -> ARWanPPP:
    """Build the PPP / PPPoE config for a unit."""

    return ARWanPPP(
        echo=_idx(indexed, ARNvramIndexType.WAN_PPP_ECHO, index),
        echo_interval=_idx(
            indexed, ARNvramIndexType.WAN_PPP_ECHO_INTERVAL, index
        ),
        echo_failure=_idx(
            indexed, ARNvramIndexType.WAN_PPP_ECHO_FAILURE, index
        ),
        conn=_idx(indexed, ARNvramIndexType.WAN_PPP_CONN, index),
        heartbeat=_idx(indexed, ARNvramIndexType.WAN_HEARTBEAT, index),
        pppoe_ac=_idx(indexed, ARNvramIndexType.WAN_PPPOE_AC, index),
        pppoe_hostuniq=_idx(
            indexed, ARNvramIndexType.WAN_PPPOE_HOSTUNIQ, index
        ),
        pppoe_idletime=_idx(
            indexed, ARNvramIndexType.WAN_PPPOE_IDLETIME, index
        ),
        pppoe_mru=_idx(indexed, ARNvramIndexType.WAN_PPPOE_MRU, index),
        pppoe_mtu=_idx(indexed, ARNvramIndexType.WAN_PPPOE_MTU, index),
        pppoe_options=_idx(indexed, ARNvramIndexType.WAN_PPPOE_OPTIONS, index),
        pppoe_service=_idx(indexed, ARNvramIndexType.WAN_PPPOE_SERVICE, index),
    )


def _build_softwire(
    values: dict[Any, Any], indexed: _Indexed, index: int
) -> ARWanSoftwire:
    """Build the Softwire46 config for a unit (global AFTR/B4 included)."""

    return ARWanSoftwire(
        dslite_mode=_idx(indexed, ARNvramIndexType.WAN_S46_DSLITE_MODE, index),
        dslite_service=_idx(
            indexed, ARNvramIndexType.WAN_S46_DSLITE_SVC, index
        ),
        aftr=values.get(ARNvramType.WAN_S46_AFTR),
        b4addr=values.get(ARNvramType.WAN_S46_B4ADDR),
        peer=_idx(indexed, ARNvramIndexType.WAN_S46_PEER, index),
        prefix4=_idx(indexed, ARNvramIndexType.WAN_S46_PREFIX4, index),
        prefix4_len=_idx(indexed, ARNvramIndexType.WAN_S46_PREFIX4LEN, index),
        prefix6=_idx(indexed, ARNvramIndexType.WAN_S46_PREFIX6, index),
        prefix6_len=_idx(indexed, ARNvramIndexType.WAN_S46_PREFIX6LEN, index),
        ea_len=_idx(indexed, ARNvramIndexType.WAN_S46_EALEN, index),
        offset=_idx(indexed, ARNvramIndexType.WAN_S46_OFFSET, index),
        psid=_idx(indexed, ARNvramIndexType.WAN_S46_PSID, index),
        psid_len=_idx(indexed, ARNvramIndexType.WAN_S46_PSIDLEN, index),
    )


def _build_unit(
    values: dict[Any, Any], indexed: _Indexed, index: int
) -> ARWanUnit:
    """Build a single WAN unit from translated values."""

    link_member = (
        ARNvramType.LINK_WAN0 if index == 0 else ARNvramType.LINK_WAN1
    )

    dns_servers = [
        dns
        for dns in (
            _idx(indexed, ARNvramIndexType.WAN_DNS1, index),
            _idx(indexed, ARNvramIndexType.WAN_DNS2, index),
        )
        if dns is not None
    ]

    return ARWanUnit(
        index=index,
        enable=bool(_idx(indexed, ARNvramIndexType.WAN_ENABLE, index)),
        primary=bool(_idx(indexed, ARNvramIndexType.WAN_PRIMARY, index)),
        protocol=_idx(
            indexed,
            ARNvramIndexType.WAN_PROTO,
            index,
            ARConnectionMethod.UNKNOWN,
        ),
        status=_idx(
            indexed,
            ARNvramIndexType.WAN_STATE,
            index,
            ARConnectionStatus.UNKNOWN,
        ),
        status_sub=_idx(
            indexed,
            ARNvramIndexType.WAN_STATE_SUB,
            index,
            ARConnectionStatus.UNKNOWN,
        ),
        status_aux=_idx(
            indexed,
            ARNvramIndexType.WAN_STATE_AUX,
            index,
            ARConnectionStatus.UNKNOWN,
        ),
        link=bool(values.get(link_member)),
        real_ip=_idx(indexed, ARNvramIndexType.WAN_REALIP, index),
        real_ip_state=bool(
            _idx(indexed, ARNvramIndexType.WAN_REALIP_STATE, index)
        ),
        main=_build_address(indexed, index, extra=False),
        extra=_build_address(indexed, index, extra=True),
        mtu=_idx(indexed, ARNvramIndexType.WAN_MTU, index),
        nat=bool(_idx(indexed, ARNvramIndexType.WAN_NAT, index)),
        dhcp_enable=bool(
            _idx(indexed, ARNvramIndexType.WAN_DHCP_ENABLE, index)
        ),
        dns_auto=bool(_idx(indexed, ARNvramIndexType.WAN_DNS_ENABLE, index)),
        dns_servers=dns_servers,
        hostname=_idx(indexed, ARNvramIndexType.WAN_HOSTNAME, index),
        client_id=_idx(indexed, ARNvramIndexType.WAN_CLIENTID, index),
        vendor_id=_idx(indexed, ARNvramIndexType.WAN_VENDORID, index),
        mac_clone=_idx(indexed, ARNvramIndexType.WAN_MAC_CLONE, index),
        vlan=_build_vlan(indexed, index),
        ppp=_build_ppp(indexed, index),
        softwire=_build_softwire(values, indexed, index),
        routing_isp=_idx(indexed, ARNvramIndexType.WAN_ROUTING_ISP, index),
        routing_isp_enable=bool(
            _idx(indexed, ARNvramIndexType.WAN_ROUTING_ISP_ENABLE, index)
        ),
        isp_country=_idx(indexed, ARNvramIndexType.WAN_ISP_COUNTRY, index),
        isp_list=_idx(indexed, ARNvramIndexType.WAN_ISP_LIST, index),
        isp_num=_idx(indexed, ARNvramIndexType.WAN_ISP_NUM, index),
    )


def _build_dualwan(values: dict[Any, Any]) -> ARDualWan | None:
    """Build the dual WAN config, or None when not reported."""

    mode = values.get(ARNvramType.DUAL_WAN_MODE)
    priority = [
        item
        for item in (values.get(ARNvramType.DUAL_WAN_CONFIG) or [])
        if item
    ]
    if mode is None and not priority:
        return None

    state = len(priority) > 1 and priority[1] != "none"
    return ARDualWan(
        mode=ARDualWanMode.from_value(mode),
        priority=priority,
        state=state,
        capability=values.get(ARNvramType.DUAL_WAN_CAPABILITY) or [],
        lan_port=values.get(ARNvramType.DUAL_WAN_LANPORT),
        lb_ratio=_parse_lb_ratio(values.get(ARNvramType.DUAL_WAN_LB_RATIO)),
        standby=bool(values.get(ARNvramType.DUAL_WAN_STANDBY)),
        routing=bool(values.get(ARNvramType.DUAL_WAN_ROUTING)),
        usb_backup=bool(values.get(ARNvramType.DUAL_WAN_USB_BACKUP)),
        autodetect=bool(values.get(ARNvramType.WAN_AUTODETECT)),
        extwan=bool(values.get(ARNvramType.DUAL_WAN_EXTWAN)),
    )


def _build_aggregation(values: dict[Any, Any]) -> ARWanAggregation | None:
    """Build the WAN aggregation config, or None when not reported."""

    state = values.get(ARNvramType.WAN_AGGREGATION)
    ports = values.get(ARNvramType.WAN_AGGREGATION_PORTS)
    if state is None and not ports:
        return None

    return ARWanAggregation(state=bool(state), ports=ports or [])


def _build_watchdog(values: dict[Any, Any]) -> ARWanWatchdog | None:
    """Build the failover watchdog config, or None when not reported."""

    enable = values.get(ARNvramType.WATCHDOG_ENABLE)
    if enable is None:
        return None

    return ARWanWatchdog(
        enable=bool(enable),
        target=values.get(ARNvramType.WATCHDOG_TARGET) or None,
        interval=values.get(ARNvramType.WATCHDOG_INTERVAL),
        max_fail=values.get(ARNvramType.WATCHDOG_MAX_FAIL),
        failback_count=values.get(ARNvramType.WATCHDOG_FAILBACK_COUNT),
    )


async def get_state(
    callback: ARCallbackType,
    source: ARWanSource,
    *,
    get_data_callback: ARCallbackType | None = None,
    **kwargs: Any,
) -> dict[Any, Any]:
    """Fetch the WAN state in a single batched NVRAM request."""

    if get_data_callback is None:
        return {}

    values = await get_data_callback(_WAN_REQUEST)
    return values if isinstance(values, dict) else {}


def translate_state(data: Any, **kwargs: Any) -> ARWan:
    """Translate the fetched WAN state into an `ARWan`."""

    if not isinstance(data, dict):
        return ARWan()

    # Re-key indexed values by (kind, index) once, so per-field lookups
    # are plain dict gets and not fresh source-object constructions
    indexed: _Indexed = {
        (key.kind, key.index): value
        for key, value in data.items()
        if isinstance(key, ARNvramIndexSource)
    }

    return ARWan(
        active_unit=data.get(ARNvramType.WAN_UNIT),
        units={
            index: _build_unit(data, indexed, index) for index in _WAN_UNITS
        },
        dualwan=_build_dualwan(data),
        aggregation=_build_aggregation(data),
        watchdog=_build_watchdog(data),
        internet_status=data.get(
            ARNvramType.LINK_INTERNET, ARConnectionStatus.UNKNOWN
        ),
    )


ARCallReg.register_module(
    ARWanSource, get_state=get_state, translate_state=translate_state
)
