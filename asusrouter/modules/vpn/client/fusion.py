"""VPN Fusion client backend for the VPN module."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from asusrouter.modules.common.command import ARService
from asusrouter.modules.endpoint_v2.hooks import ARHook
from asusrouter.modules.vpn.enums import (
    ARVpnClientField,
    ARVpnProtocol,
    ARVpnState,
)
from asusrouter.tools.converters_v2.raw import (
    raw_to_bool,
    raw_to_int,
    raw_to_str,
)
from asusrouter.tools.identifiers import IpAddress, IpInterface, Password
from asusrouter.tools.identifiers.ip import read_ip_interface_list

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

# WireGuard client nvram suffix -> field, converter (`wgc{unit}_{suffix}`)
_WG: tuple[tuple[str, ARVpnClientField, Callable[[Any], Any]], ...] = (
    ("priv", ARVpnClientField.PRIVATE_KEY, Password.from_value_safe),
    ("addr", ARVpnClientField.ADDRESS, IpInterface.from_value_safe),
    ("dns", ARVpnClientField.DNS, IpAddress.from_value_safe),
    ("mtu", ARVpnClientField.MTU, raw_to_int),
    ("ppub", ARVpnClientField.PUBLIC_KEY, raw_to_str),
    ("psk", ARVpnClientField.PSK, Password.from_value_safe),
    ("aips", ARVpnClientField.ALLOWED_IPS, read_ip_interface_list),
    ("ep_addr", ARVpnClientField.ENDPOINT_ADDRESS, IpAddress.from_value_safe),
    ("ep_port", ARVpnClientField.ENDPOINT_PORT, raw_to_int),
    ("alive", ARVpnClientField.KEEPALIVE, raw_to_int),
    ("nat", ARVpnClientField.NAT, raw_to_bool),
)


@dataclass(frozen=True)
class _Context:
    """Router-global data shared by every profile in one translate pass."""

    data: dict[str, Any]
    pptp_options: list[str]
    status: dict[int, tuple[ARVpnState, int | None]]
    support: dict[int, bool]
    default_wan: int | None


def nvram_keys() -> list[str]:
    """Return the nvram keys required to read all Fusion client profiles."""

    keys = ["vpnc_clientlist", "vpnc_pptp_options_x_list", "vpnc_default_wan"]
    for unit in WG_UNITS:
        keys.extend(f"wgc{unit}_{suffix}" for suffix, _, _ in _WG)
    return keys


def _convert(raw: Any, converter: Callable[[Any], Any]) -> Any:
    """Convert a raw value, treating empty/absent as no value."""

    if raw is None or raw == "":
        return None
    value = converter(raw)
    return None if value == [] else value


def _get(parts: list[str], index: int) -> str | None:
    """Return a `>`-split field, or None when absent."""

    return parts[index] if index < len(parts) else None


def _split_rows(raw: Any) -> list[str]:
    """Decode a nvram list and split it into `<`-delimited rows."""

    text = raw_to_str(raw)
    if text is None:
        return []
    text = text.replace("&#60", "<").replace("&#62", ">")
    return text.split("<")


def _status(data: dict[str, Any]) -> dict[int, tuple[ARVpnState, int | None]]:
    """Map vpnc_idx -> (state, reason) from the status hook."""

    status: dict[int, tuple[ARVpnState, int | None]] = {}
    for row in _split_rows(data.get(STATUS_HOOK.value)):
        parts = row.split(">")
        vpnc_idx = raw_to_int(_get(parts, _S_VPNC_IDX))
        if vpnc_idx is None:
            continue
        code = raw_to_int(_get(parts, _S_STATUS))
        state = (
            _STATE_MAP.get(code, ARVpnState.UNKNOWN)
            if code is not None
            else ARVpnState.UNKNOWN
        )
        status[vpnc_idx] = (state, raw_to_int(_get(parts, _S_REASON)))
    return status


def _default_wan_support(data: dict[str, Any]) -> dict[int, bool]:
    """Map vpnc_idx -> whether the profile supports default-WAN routing."""

    support: dict[int, bool] = {}
    for row in _split_rows(data.get(NONDEF_WAN_HOOK.value)):
        parts = row.split(">")
        vpnc_idx = raw_to_int(_get(parts, 0))
        if vpnc_idx is None:
            continue
        # `0` means the profile is allowed on the default WAN
        support[vpnc_idx] = _get(parts, 1) == "0"
    return support


def _wireguard(data: dict[str, Any], unit: int) -> dict[ARVpnClientField, Any]:
    """Read the `wgc{unit}_*` peer config of a WireGuard client."""

    fields: dict[ARVpnClientField, Any] = {}
    for suffix, field, converter in _WG:
        value = _convert(data.get(f"wgc{unit}_{suffix}"), converter)
        if value is not None:
            fields[field] = value
    return fields


def _base_fields(
    parts: list[str], position: int
) -> dict[ARVpnClientField, Any]:
    """Build the clientlist-derived fields of a profile."""

    protocol = ARVpnProtocol.from_value(_get(parts, _F_PROTO))
    server_int = raw_to_int(_get(parts, _F_SERVER))
    server = server_int if server_int is not None else _get(parts, _F_SERVER)

    fields: dict[ARVpnClientField, Any] = {
        ARVpnClientField.NAME: raw_to_str(_get(parts, _F_NAME)),
        ARVpnClientField.PROTOCOL: protocol,
        ARVpnClientField.UNIT: position,
        ARVpnClientField.ENABLED: _get(parts, _F_ACTIVATE) == "1",
    }
    if server not in (None, ""):
        fields[ARVpnClientField.SERVER] = server

    vpnc_idx = raw_to_int(_get(parts, _F_VPNC_IDX))
    if vpnc_idx is not None:
        fields[ARVpnClientField.VPNC_INDEX] = vpnc_idx

    for index, field, converter in _INFO:
        value = _convert(_get(parts, index), converter)
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
    if raw_to_str(_get(parts, _F_NAME)) is None:
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

    rows = _split_rows(data.get("vpnc_clientlist"))
    if not rows:
        return {}

    # Parallel list; a leading empty aligns it one ahead of the clientlist
    ctx = _Context(
        data=data,
        pptp_options=_split_rows(data.get("vpnc_pptp_options_x_list"))[1:],
        status=_status(data),
        support=_default_wan_support(data),
        default_wan=raw_to_int(data.get("vpnc_default_wan")),
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

    rows = _split_rows(clientlist_raw)
    position = 0
    target: int | None = None
    for index, row in enumerate(rows):
        if row == "":
            continue
        parts = row.split(">")
        if (
            ARVpnProtocol.from_value(_get(parts, _F_PROTO)) is protocol
            and raw_to_int(_get(parts, _F_SERVER)) == unit
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
        "vpnc_unit": target,
        "vpnc_clientlist": "<".join(rows),
    }
    return [service], arguments
