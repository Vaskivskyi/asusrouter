"""Classic (non-Fusion) VPN client backend for the VPN module."""

from __future__ import annotations

from collections.abc import Callable
import re
from typing import TYPE_CHECKING, Any

from asusrouter.modules.vpn.client.fusion import _WG, _convert
from asusrouter.modules.vpn.enums import (
    ARVpnClientField,
    ARVpnProtocol,
    ARVpnState,
)
from asusrouter.tools.converters_v2.raw import raw_to_int, raw_to_str
from asusrouter.tools.identifiers import IpAddress

if TYPE_CHECKING:
    from asusrouter.modules.service.action import ARServiceInput

# Client units exposed by the firmware
UNITS = (1, 2, 3, 4, 5)

# Key under which the source stashes the ajax_vpn_status result
STATUS_KEY = "_vpn_status"

# Values that mean "no data" in the status endpoint
_EMPTY = ("", "None")

# OpenVPN client nvram suffix -> field, converter (`vpn_client{unit}_*`)
_OVPN: tuple[tuple[str, ARVpnClientField, Callable[[Any], Any]], ...] = (
    ("desc", ARVpnClientField.NAME, raw_to_str),
    ("addr", ARVpnClientField.SERVER, raw_to_str),
    ("port", ARVpnClientField.ENDPOINT_PORT, raw_to_int),
    ("username", ARVpnClientField.USERNAME, raw_to_str),
)

# vpn.cgi status token -> field, converter (parsed from `vpn_client{n}_status`)
_STATS: tuple[tuple[str, ARVpnClientField, Callable[[Any], Any]], ...] = (
    ("Updated", ARVpnClientField.CONNECTED_SINCE, raw_to_str),
    ("TCP/UDP read bytes", ARVpnClientField.RX_BYTES, raw_to_int),
    ("TCP/UDP write bytes", ARVpnClientField.TX_BYTES, raw_to_int),
    ("TUN/TAP read bytes", ARVpnClientField.TUN_TAP_RX_BYTES, raw_to_int),
    ("TUN/TAP write bytes", ARVpnClientField.TUN_TAP_TX_BYTES, raw_to_int),
    ("Auth read bytes", ARVpnClientField.AUTH_RX_BYTES, raw_to_int),
    ("pre-compress bytes", ARVpnClientField.PRE_COMPRESS_BYTES, raw_to_int),
    ("post-compress bytes", ARVpnClientField.POST_COMPRESS_BYTES, raw_to_int),
    (
        "pre-decompress bytes",
        ARVpnClientField.PRE_DECOMPRESS_BYTES,
        raw_to_int,
    ),
    (
        "post-decompress bytes",
        ARVpnClientField.POST_DECOMPRESS_BYTES,
        raw_to_int,
    ),
)


def nvram_keys() -> list[str]:
    """Return the nvram keys required to read every classic client unit."""

    keys = ["vpn_clientx_eas"]
    for unit in UNITS:
        keys.append(f"vpn_client{unit}_state")
        keys.append(f"vpn_client{unit}_errno")
        keys.extend(f"vpn_client{unit}_{suffix}" for suffix, _, _ in _OVPN)
        keys.append(f"wgc{unit}_enable")
        keys.extend(f"wgc{unit}_{suffix}" for suffix, _, _ in _WG)
    return keys


def _clean(value: Any) -> str | None:
    """Return a status value, or None when it is a placeholder."""

    text = raw_to_str(value)
    return None if text is None or text in _EMPTY else text


def _ip(value: Any) -> IpAddress | None:
    """Parse an IP, treating the unspecified address (all-zero) as absent."""

    ip = IpAddress.from_value_safe(_clean(value))
    return ip if ip is not None and ip.to_int() != 0 else None


def _status_data(data: dict[str, Any]) -> dict[str, Any]:
    """Return the ajax_vpn_status block the source stashed, if any."""

    status = data.get(STATUS_KEY)
    return status if isinstance(status, dict) else {}


def _enabled_units(data: dict[str, Any]) -> set[int]:
    """Parse `vpn_clientx_eas` into the set of active OpenVPN units."""

    text = raw_to_str(data.get("vpn_clientx_eas"))
    if text is None:
        return set()
    return {n for part in text.split(",") if (n := raw_to_int(part))}


def _parse_status(raw: Any) -> dict[ARVpnClientField, Any]:
    """Parse a `vpn_client{n}_status` string into live fields."""

    text = _clean(raw)
    if text is None:
        return {}

    fields: dict[ARVpnClientField, Any] = {}
    remote = re.search(r"REMOTE,(.*?)(?=>)", text)
    if remote:
        host = remote[1].partition(",")[0]
        address, _, port = host.rpartition(":")
        ip = _ip(address or host)
        if ip is not None:
            fields[ARVpnClientField.REMOTE_ADDRESS] = ip
        remote_port = raw_to_int(port) if address else None
        if remote_port is not None:
            fields[ARVpnClientField.REMOTE_PORT] = remote_port

    for token, field, converter in _STATS:
        match = re.search(rf"{re.escape(token)},(.*?)(?=>)", text)
        value = _convert(match[1] if match else None, converter)
        if value is not None:
            fields[field] = value

    return fields


def _openvpn(
    data: dict[str, Any],
    status: dict[str, Any],
    unit: int,
    enabled: set[int],
) -> dict[ARVpnClientField, Any] | None:
    """Build an OpenVPN client profile, or None when the unit is empty."""

    fields: dict[ARVpnClientField, Any] = {}
    for suffix, field, converter in _OVPN:
        value = _convert(data.get(f"vpn_client{unit}_{suffix}"), converter)
        if value is not None:
            fields[field] = value

    state = _convert(
        data.get(f"vpn_client{unit}_state"), ARVpnState.from_value
    )
    if state is not None:
        fields[ARVpnClientField.STATE] = state
        if state is ARVpnState.ERROR:
            errno = _convert(data.get(f"vpn_client{unit}_errno"), raw_to_int)
            if errno is not None:
                fields[ARVpnClientField.STATE_REASON] = errno

    if not fields:
        return None

    fields[ARVpnClientField.PROTOCOL] = ARVpnProtocol.OPENVPN
    fields[ARVpnClientField.UNIT] = unit
    fields[ARVpnClientField.ENABLED] = unit in enabled

    address = _ip(status.get(f"vpn_client{unit}_ip"))
    if address is not None:
        fields[ARVpnClientField.ADDRESS] = address
    fields.update(_parse_status(status.get(f"vpn_client{unit}_status")))

    return fields


def _wireguard(
    data: dict[str, Any], unit: int
) -> dict[ARVpnClientField, Any] | None:
    """Build a WireGuard client profile, or None when the unit is empty."""

    fields: dict[ARVpnClientField, Any] = {}
    for suffix, field, converter in _WG:
        value = _convert(data.get(f"wgc{unit}_{suffix}"), converter)
        if value is not None:
            fields[field] = value

    enable = _convert(data.get(f"wgc{unit}_enable"), raw_to_int)
    if enable is None and not fields:
        return None

    fields[ARVpnClientField.PROTOCOL] = ARVpnProtocol.WIREGUARD
    fields[ARVpnClientField.UNIT] = unit
    fields[ARVpnClientField.ENABLED] = enable == 1
    return fields


def translate(
    data: dict[str, Any],
) -> dict[ARVpnProtocol, dict[int, dict[ARVpnClientField, Any]]]:
    """Translate raw data into classic client profiles grouped by protocol."""

    status = _status_data(data)
    enabled = _enabled_units(data)

    result: dict[ARVpnProtocol, dict[int, dict[ARVpnClientField, Any]]] = {}
    for unit in UNITS:
        ovpn = _openvpn(data, status, unit, enabled)
        if ovpn is not None:
            result.setdefault(ARVpnProtocol.OPENVPN, {})[unit] = ovpn
        wg = _wireguard(data, unit)
        if wg is not None:
            result.setdefault(ARVpnProtocol.WIREGUARD, {})[unit] = wg

    return result


def build_toggle_payload(
    protocol: ARVpnProtocol, unit: int, state: bool
) -> tuple[list[ARServiceInput], dict[str, Any]] | None:
    """Build the `(services, arguments)` to toggle a classic client, or None.

    OpenVPN clients use the per-unit `start/stop_vpnclient{unit}` service;
    WireGuard clients use `start/stop_wgc {unit}` with the enable flag.
    """

    if protocol is ARVpnProtocol.OPENVPN:
        service = (
            f"start_vpnclient{unit}" if state else f"stop_vpnclient{unit}"
        )
        return [service], {"id": unit}

    if protocol is ARVpnProtocol.WIREGUARD:
        service = f"start_wgc {unit}" if state else f"stop_wgc {unit}"
        arguments: dict[str, Any] = {
            "wgc_enable": int(state),
            "wgc_unit": unit,
            "id": unit,
        }
        return [service], arguments

    return None
