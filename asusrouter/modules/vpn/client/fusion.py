"""VPN Fusion client backend for the VPN module."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from asusrouter.modules.common.command import ARService
from asusrouter.modules.endpoint.hooks import ARHook
from asusrouter.modules.nvram import (
    ARNvramIndexSource,
    ARNvramIndexType,
    ARNvramItem,
    ARNvramType,
)
from asusrouter.modules.vpn.enums import (
    ARVpnClientField,
    ARVpnProtocol,
    ARVpnState,
)
from asusrouter.tools.converters.raw import (
    raw_convert,
    raw_to_bool,
    raw_to_int,
    raw_to_str,
)
from asusrouter.tools.identifiers import IpAddress, IpInterface, Password
from asusrouter.tools.identifiers.ip import read_ip_interface_list
from asusrouter.tools.readers.nvram_list import get_field, split_rows
from asusrouter.tools.readers.table import read_table

if TYPE_CHECKING:
    from asusrouter.modules.service.action import ARServiceInput

STATUS_HOOK = ARHook.VPNC_STATUS
NONDEF_WAN_HOOK = ARHook.VPNC_NONDEF_WAN_PROFILES

# WireGuard client units to probe; OpenVPN client config is in the clientlist
WG_UNITS = (1, 2, 3, 4, 5)

# clientlist `>`-field positions
_F_NAME = 0
_F_PROTO = 1
_F_SERVER = 2
_F_USERNAME = 3
_F_PASSWORD = 4
_F_ACTIVATE = 5
_F_VPNC_IDX = 6
_F_REGION = 7

# get_vpnc_status `>`-field positions
_S_STATUS = 0
_S_REASON = 1
_S_VPNC_IDX = 2

# Live status code -> unified state
_STATE_MAP = {
    0: ARVpnState.ERROR,
    1: ARVpnState.CONNECTING,
    2: ARVpnState.CONNECTED,
    4: ARVpnState.ERROR,
    5: ARVpnState.DISCONNECTED,
    6: ARVpnState.ERROR,
}

# clientlist string field -> profile field, converter
_INFO: tuple[tuple[int, ARVpnClientField, Callable[[Any], Any]], ...] = (
    (_F_USERNAME, ARVpnClientField.USERNAME, raw_to_str),
    (_F_PASSWORD, ARVpnClientField.PASSWORD, Password.from_value_safe),
    (_F_REGION, ARVpnClientField.REGION, raw_to_str),
)

# WireGuard client nvram key -> field, converter (`wgc{unit}_*`)
_WG: tuple[
    tuple[ARNvramIndexType, ARVpnClientField, Callable[[Any], Any]], ...
] = (
    (
        ARNvramIndexType.WGC_PRIV,
        ARVpnClientField.PRIVATE_KEY,
        Password.from_value_safe,
    ),
    (
        ARNvramIndexType.WGC_ADDR,
        ARVpnClientField.ADDRESS,
        IpInterface.from_value_safe,
    ),
    (
        ARNvramIndexType.WGC_DNS,
        ARVpnClientField.DNS,
        IpAddress.from_value_safe,
    ),
    (ARNvramIndexType.WGC_MTU, ARVpnClientField.MTU, raw_to_int),
    (ARNvramIndexType.WGC_PPUB, ARVpnClientField.PUBLIC_KEY, raw_to_str),
    (
        ARNvramIndexType.WGC_PSK,
        ARVpnClientField.PSK,
        Password.from_value_safe,
    ),
    (
        ARNvramIndexType.WGC_AIPS,
        ARVpnClientField.ALLOWED_IPS,
        read_ip_interface_list,
    ),
    (
        ARNvramIndexType.WGC_EP_ADDR,
        ARVpnClientField.ENDPOINT_ADDRESS,
        IpAddress.from_value_safe,
    ),
    (
        ARNvramIndexType.WGC_EP_PORT,
        ARVpnClientField.ENDPOINT_PORT,
        raw_to_int,
    ),
    (ARNvramIndexType.WGC_ALIVE, ARVpnClientField.KEEPALIVE, raw_to_int),
    (ARNvramIndexType.WGC_NAT, ARVpnClientField.NAT, raw_to_bool),
)


@dataclass(frozen=True)
class _Context:
    """Router-global data shared by every profile in one translate pass."""

    data: dict[str, Any]
    pptp_options: list[str]
    status: dict[int, tuple[ARVpnState, int | None]]
    support: dict[int, bool]
    default_wan: int | None


def nvram_items() -> list[ARNvramItem]:
    """Return the nvram items required to read all Fusion client profiles."""

    items: list[ARNvramItem] = [
        ARNvramType.VPNC_CLIENTLIST,
        ARNvramType.VPNC_PPTP_OPTIONS,
        ARNvramType.VPNC_DEFAULT_WAN,
    ]
    for unit in WG_UNITS:
        items.extend(ARNvramIndexSource(kind, unit) for kind, _, _ in _WG)
    return items


def _status(data: dict[str, Any]) -> dict[int, tuple[ARVpnState, int | None]]:
    """Map vpnc_idx -> (state, reason) from the status hook."""

    status: dict[int, tuple[ARVpnState, int | None]] = {}
    for row in split_rows(data.get(STATUS_HOOK.value)):
        parts = row.split(">")
        vpnc_idx = raw_to_int(get_field(parts, _S_VPNC_IDX))
        if vpnc_idx is None:
            continue
        code = raw_to_int(get_field(parts, _S_STATUS))
        state = (
            _STATE_MAP.get(code, ARVpnState.UNKNOWN)
            if code is not None
            else ARVpnState.UNKNOWN
        )
        status[vpnc_idx] = (state, raw_to_int(get_field(parts, _S_REASON)))
    return status


def _default_wan_support(data: dict[str, Any]) -> dict[int, bool]:
    """Map vpnc_idx -> whether the profile supports default-WAN routing."""

    support: dict[int, bool] = {}
    for row in split_rows(data.get(NONDEF_WAN_HOOK.value)):
        parts = row.split(">")
        vpnc_idx = raw_to_int(get_field(parts, 0))
        if vpnc_idx is None:
            continue
        # `0` means the profile is allowed on the default WAN
        support[vpnc_idx] = get_field(parts, 1) == "0"
    return support


def _wireguard(data: dict[str, Any], unit: int) -> dict[ARVpnClientField, Any]:
    """Read the `wgc{unit}_*` peer config of a WireGuard client."""

    return read_table(data, _WG, key=lambda kind: kind.key(unit))


def _base_fields(
    parts: list[str], position: int
) -> dict[ARVpnClientField, Any]:
    """Build the clientlist-derived fields of a profile."""

    protocol = ARVpnProtocol.from_value(get_field(parts, _F_PROTO))
    server_int = raw_to_int(get_field(parts, _F_SERVER))
    server = (
        server_int if server_int is not None else get_field(parts, _F_SERVER)
    )

    fields: dict[ARVpnClientField, Any] = {
        ARVpnClientField.NAME: raw_to_str(get_field(parts, _F_NAME)),
        ARVpnClientField.PROTOCOL: protocol,
        ARVpnClientField.UNIT: position,
        ARVpnClientField.ENABLED: get_field(parts, _F_ACTIVATE) == "1",
    }
    if server not in (None, ""):
        fields[ARVpnClientField.SERVER] = server

    vpnc_idx = raw_to_int(get_field(parts, _F_VPNC_IDX))
    if vpnc_idx is not None:
        fields[ARVpnClientField.VPNC_INDEX] = vpnc_idx

    for index, field, converter in _INFO:
        value = raw_convert(get_field(parts, index), converter)
        if value is not None:
            fields[field] = value

    return fields


def _apply_routing(
    fields: dict[ARVpnClientField, Any], vpnc_idx: int, ctx: _Context
) -> None:
    """Add live status and default-WAN routing keyed by vpnc_idx."""

    state = ctx.status.get(vpnc_idx)
    if state is not None:
        fields[ARVpnClientField.STATE] = state[0]
        # The reason code is only meaningful for a failed connection
        if state[0] is ARVpnState.ERROR and state[1] is not None:
            fields[ARVpnClientField.STATE_REASON] = state[1]
    if vpnc_idx in ctx.support:
        fields[ARVpnClientField.DEFAULT_WAN_SUPPORT] = ctx.support[vpnc_idx]
    if ctx.default_wan is not None:
        fields[ARVpnClientField.DEFAULT_WAN] = vpnc_idx == ctx.default_wan


def _profile(
    row: str, position: int, ctx: _Context
) -> dict[ARVpnClientField, Any] | None:
    """Build a single client profile, or None when the row is empty."""

    parts = row.split(">")
    if raw_to_str(get_field(parts, _F_NAME)) is None:
        return None

    fields = _base_fields(parts, position)

    option = (
        ctx.pptp_options[position]
        if position < len(ctx.pptp_options)
        else None
    )
    if option not in (None, "", "auto"):
        fields[ARVpnClientField.PPTP_OPTIONS] = option

    vpnc_idx = fields.get(ARVpnClientField.VPNC_INDEX)
    if vpnc_idx is not None:
        _apply_routing(fields, vpnc_idx, ctx)

    server = fields.get(ARVpnClientField.SERVER)
    if fields[ARVpnClientField.PROTOCOL] is ARVpnProtocol.WIREGUARD and (
        isinstance(server, int)
    ):
        fields.update(_wireguard(ctx.data, server))

    return fields


def translate(
    data: dict[str, Any],
) -> dict[ARVpnProtocol, dict[int, dict[ARVpnClientField, Any]]]:
    """Translate raw data into client profiles grouped by protocol."""

    rows = split_rows(data.get(ARNvramType.VPNC_CLIENTLIST.value))
    if not rows:
        return {}

    # Parallel list; a leading empty aligns it one ahead of the clientlist
    ctx = _Context(
        data=data,
        pptp_options=split_rows(data.get(ARNvramType.VPNC_PPTP_OPTIONS.value))[
            1:
        ],
        status=_status(data),
        support=_default_wan_support(data),
        default_wan=raw_to_int(data.get(ARNvramType.VPNC_DEFAULT_WAN.value)),
    )

    result: dict[ARVpnProtocol, dict[int, dict[ARVpnClientField, Any]]] = {}
    position = 0
    for row in rows:
        if row == "":
            continue
        fields = _profile(row, position, ctx)
        vpnc_idx = (
            fields.get(ARVpnClientField.VPNC_INDEX, position)
            if (fields is not None)
            else None
        )
        position += 1
        if fields is None or vpnc_idx is None:
            continue
        protocol = fields[ARVpnClientField.PROTOCOL]
        result.setdefault(protocol, {})[vpnc_idx] = fields

    return result


def build_toggle_payload(
    clientlist_raw: Any,
    protocol: ARVpnProtocol,
    unit: int,
    state: bool,
) -> tuple[list[ARServiceInput], dict[str, Any]] | None:
    """Build the `(services, arguments)` to toggle a Fusion client, or None.

    Locates the profile of `protocol` with server unit `unit`, flips its
    activate flag in a rewritten `vpnc_clientlist`, and targets it by position
    (`vpnc_unit`), mirroring the web UI's `restart_vpnc` / `stop_vpnc` toggle.
    """

    rows = split_rows(clientlist_raw)
    position = 0
    target: int | None = None
    for index, row in enumerate(rows):
        if row == "":
            continue
        parts = row.split(">")
        if (
            ARVpnProtocol.from_value(get_field(parts, _F_PROTO)) is protocol
            and raw_to_int(get_field(parts, _F_SERVER)) == unit
            and len(parts) > _F_ACTIVATE
        ):
            parts[_F_ACTIVATE] = "1" if state else "0"
            rows[index] = ">".join(parts)
            target = position
            break
        position += 1

    if target is None:
        return None

    service = ARService.VPNC_RESTART if state else ARService.VPNC_STOP
    arguments: dict[str, Any] = {
        ARNvramType.VPNC_UNIT.value: target,
        ARNvramType.VPNC_CLIENTLIST.value: "<".join(rows),
    }
    return [service], arguments
