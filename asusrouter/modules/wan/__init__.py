"""WAN module for AsusRouter."""

from __future__ import annotations

from dataclasses import dataclass, field
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
from asusrouter.modules.endpoint_v2.hooks import ARHook, hook_request
from asusrouter.modules.nvram import (
    ARNvramIndexSource,
    ARNvramIndexType,
    ARNvramItem,
    ARNvramType,
)
from asusrouter.modules.source import ARDataSource
from asusrouter.registry import (
    ARCallableEntry,
    ARCallableRegistry as ARCallReg,
)
from asusrouter.tools.converters_v2.raw import raw_to_int
from asusrouter.tools.enum import FromStrMixin
from asusrouter.tools.identifiers.ip import IpAddress
from asusrouter.tools.types import ARCallbackType

__all__ = [
    "ARDualWan",
    "ARDualWanMode",
    "ARWANCapability",
    "ARWan",
    "ARWanAddress",
    "ARWanAggregation",
    "ARWanSource",
    "ARWanSourceUniversal",
    "ARWanUnit",
]


class ARDualWanMode(FromStrMixin, StrEnum):
    """Dual WAN operating mode."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    FAILOVER = "fo"
    FALLBACK = "fb"
    LOAD_BALANCE = "lb"


class ARWANCapability(FromStrMixin, StrEnum):
    """WAN capabilities."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    AGGREGATION = "aggregation"
    DUALWAN = "dualwan"


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
class ARWanUnit:
    """A single WAN unit."""

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


@dataclass
class ARDualWan:
    """Dual WAN configuration."""

    mode: ARDualWanMode = ARDualWanMode.UNKNOWN
    priority: list[str] = field(default_factory=list)
    state: bool = False


@dataclass
class ARWanAggregation:
    """WAN link aggregation configuration."""

    state: bool = False
    ports: list[str] = field(default_factory=list)


@dataclass
class ARWan:
    """The WAN state of the router."""

    active_unit: int | None = None
    units: dict[int, ARWanUnit] = field(default_factory=dict)
    dualwan: ARDualWan | None = None
    aggregation: ARWanAggregation | None = None
    internet_status: ARConnectionStatus = ARConnectionStatus.UNKNOWN


# Flat (global) NVRAM members for the WAN state
_WAN_FLAT: tuple[ARNvramType, ...] = (
    ARNvramType.DUAL_WAN_MODE,
    ARNvramType.DUAL_WAN_CONFIG,
    ARNvramType.WAN_AGGREGATION,
    ARNvramType.WAN_AGGREGATION_PORTS,
    ARNvramType.LINK_INTERNET,
    ARNvramType.LINK_WAN0,
    ARNvramType.LINK_WAN1,
)

# Indexed (per-unit) NVRAM members for the WAN state
_WAN_INDEXED: tuple[ARNvramIndexType, ...] = (
    ARNvramIndexType.WAN_ENABLE,
    ARNvramIndexType.WAN_PRIMARY,
    ARNvramIndexType.WAN_PROTO,
    ARNvramIndexType.WAN_STATE,
    ARNvramIndexType.WAN_STATE_SUB,
    ARNvramIndexType.WAN_STATE_AUX,
    ARNvramIndexType.WAN_REALIP,
    ARNvramIndexType.WAN_REALIP_STATE,
    ARNvramIndexType.WAN_DNS,
    ARNvramIndexType.WAN_DNS_X,
    ARNvramIndexType.WAN_GATEWAY,
    ARNvramIndexType.WAN_GATEWAY_X,
    ARNvramIndexType.WAN_IPADDR,
    ARNvramIndexType.WAN_IPADDR_X,
    ARNvramIndexType.WAN_LEASE,
    ARNvramIndexType.WAN_LEASE_X,
    ARNvramIndexType.WAN_NETMASK,
    ARNvramIndexType.WAN_NETMASK_X,
    ARNvramIndexType.WAN_EXPIRES,
    ARNvramIndexType.WAN_EXPIRES_X,
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

    def __eq__(self, other: object) -> bool:
        """All WAN sources are equal (router-global)."""

        if not isinstance(other, ARWanSource):
            return NotImplemented
        return True

    def __hash__(self) -> int:
        """Hash by type."""

        return hash(type(self))

    def __repr__(self) -> str:
        """Representation of the WAN source."""

        return "<ARWanSource>"


# Universal instance - preferred
ARWanSourceUniversal: ARWanSource = ARWanSource()


_Indexed = dict[tuple[ARNvramIndexType, int], Any]

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


def _build_unit(
    values: dict[Any, Any], indexed: _Indexed, index: int
) -> ARWanUnit:
    """Build a single WAN unit from translated values."""

    link_member = (
        ARNvramType.LINK_WAN0 if index == 0 else ARNvramType.LINK_WAN1
    )

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
    )


def _build_aggregation(values: dict[Any, Any]) -> ARWanAggregation | None:
    """Build the WAN aggregation config, or None when not reported."""

    state = values.get(ARNvramType.WAN_AGGREGATION)
    ports = values.get(ARNvramType.WAN_AGGREGATION_PORTS)
    if state is None and not ports:
        return None

    return ARWanAggregation(state=bool(state), ports=ports or [])


async def get_state(
    callback: ARCallbackType,
    source: ARWanSource,
    *,
    get_data_callback: ARCallbackType | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Fetch the WAN state: NVRAM values plus the active WAN unit."""

    if get_data_callback is None:
        return {}

    values = await get_data_callback(_WAN_REQUEST)

    unit_raw = await callback(
        endpoint=AREndpoint.FETCH_DATA,
        request=hook_request(ARHook.WAN_UNIT),
    )
    active_unit = (
        raw_to_int(unit_raw.get("get_wan_unit"))
        if isinstance(unit_raw, dict)
        else None
    )

    return {
        "values": values if isinstance(values, dict) else {},
        "active_unit": active_unit,
    }


def translate_state(data: Any, **kwargs: Any) -> ARWan:
    """Translate the fetched WAN state into an `ARWan`."""

    if not isinstance(data, dict):
        return ARWan()

    values: dict[Any, Any] = data.get("values") or {}

    # Re-key indexed values by (kind, index) once, so per-field lookups
    # are plain dict gets and not fresh source-object constructions
    indexed: _Indexed = {
        (key.kind, key.index): value
        for key, value in values.items()
        if isinstance(key, ARNvramIndexSource)
    }

    return ARWan(
        active_unit=data.get("active_unit"),
        units={
            index: _build_unit(values, indexed, index) for index in _WAN_UNITS
        },
        dualwan=_build_dualwan(values),
        aggregation=_build_aggregation(values),
        internet_status=values.get(
            ARNvramType.LINK_INTERNET, ARConnectionStatus.UNKNOWN
        ),
    )


calls: dict[str, ARCallableEntry] = {
    AR_CALL_GET_STATE: get_state,
    AR_CALL_TRANSLATE_STATE: translate_state,
}

ARCallReg.register(ARWanSource, **calls)
