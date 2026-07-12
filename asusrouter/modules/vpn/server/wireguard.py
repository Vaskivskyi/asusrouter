"""WireGuard server backend for the VPN module."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any
from urllib.parse import unquote

from asusrouter.modules.common.command import ARService
from asusrouter.modules.endpoint_v2.hooks import ARHook
from asusrouter.modules.nvram import (
    ARNvramIndexSource,
    ARNvramIndexType,
    ARNvramItem,
    ARNvramType,
)
from asusrouter.modules.vpn.enums import (
    ARVpnPeerField,
    ARVpnServerField,
    ARVpnState,
)
from asusrouter.tools.converters_v2.raw import (
    raw_to_bool,
    raw_to_int,
    raw_to_str,
)
from asusrouter.tools.identifiers import IpInterface, Password
from asusrouter.tools.identifiers.ip import read_ip_interface_list

if TYPE_CHECKING:
    from asusrouter.modules.service.action import ARServiceInput

# Single WireGuard server unit on current firmware
UNIT = 1

# Peer slots to probe; `get_wgsc_status` on real devices exposes ten
MAX_PEERS = 10

HOOK = ARHook.WIREGUARD_SERVER_STATUS


def _decode(value: Any) -> str | None:
    """URL-decode a percent-encoded nvram value (peer fields are encoded)."""

    text = raw_to_str(value)
    return unquote(text) if text is not None else None


def _decode_interfaces(value: Any) -> list[IpInterface]:
    """URL-decode then read a comma/whitespace list of IP interfaces."""

    return read_ip_interface_list(_decode(value))


# Server nvram key -> field, converter
_SETTINGS: tuple[
    tuple[ARNvramType, ARVpnServerField, Callable[[Any], Any]], ...
] = (
    (ARNvramType.WGS_ENABLE, ARVpnServerField.ENABLED, raw_to_bool),
    (
        ARNvramType.WGS_ADDR,
        ARVpnServerField.ADDRESS,
        IpInterface.from_value_safe,
    ),
    (ARNvramType.WGS_PORT, ARVpnServerField.PORT, raw_to_int),
    (ARNvramType.WGS_DNS, ARVpnServerField.ALLOW_DNS, raw_to_bool),
    (ARNvramType.WGS_NAT6, ARVpnServerField.NAT6, raw_to_bool),
    (ARNvramType.WGS_PSK, ARVpnServerField.PSK, raw_to_bool),
    (ARNvramType.WGS_ALIVE, ARVpnServerField.KEEPALIVE, raw_to_int),
    (ARNvramType.WGS_LANACCESS, ARVpnServerField.LAN_ACCESS, raw_to_bool),
    (ARNvramType.WGS_PUB, ARVpnServerField.PUBLIC_KEY, raw_to_str),
    (
        ARNvramType.WGS_PRIV,
        ARVpnServerField.PRIVATE_KEY,
        Password.from_value_safe,
    ),
)

# Per-peer nvram key -> field, converter (`wgs1_c{n}_*`)
_PEER: tuple[
    tuple[ARNvramIndexType, ARVpnPeerField, Callable[[Any], Any]], ...
] = (
    (ARNvramIndexType.WGS_PEER_ENABLE, ARVpnPeerField.ENABLED, raw_to_bool),
    (ARNvramIndexType.WGS_PEER_NAME, ARVpnPeerField.NAME, _decode),
    (
        ARNvramIndexType.WGS_PEER_ADDR,
        ARVpnPeerField.ADDRESS,
        _decode_interfaces,
    ),
    (
        ARNvramIndexType.WGS_PEER_AIPS,
        ARVpnPeerField.ALLOWED_IPS,
        _decode_interfaces,
    ),
    (
        ARNvramIndexType.WGS_PEER_CAIPS,
        ARVpnPeerField.CLIENT_ALLOWED_IPS,
        _decode_interfaces,
    ),
)


def build_toggle_payload(
    unit: int, state: bool
) -> tuple[list[ARServiceInput], dict[str, Any]]:
    """Build the `(services, arguments)` to enable/disable the WG server."""

    services: list[ARServiceInput] = [
        ARService.WIREGUARD_SERVER_RESTART,
        ARService.DNS_RESTART,
    ]
    arguments: dict[str, Any] = {
        ARNvramType.WGS_ENABLE.value: int(state),
        ARNvramType.WGS_UNIT.value: unit,
        "id": unit,
    }
    return services, arguments


def nvram_items() -> list[ARNvramItem]:
    """Return the nvram items to read the WireGuard server and its peers."""

    items: list[ARNvramItem] = [key for key, _, _ in _SETTINGS]
    for index in range(1, MAX_PEERS + 1):
        items.extend(ARNvramIndexSource(kind, index) for kind, _, _ in _PEER)
    return items


def _convert(raw: Any, converter: Callable[[Any], Any]) -> Any:
    """Convert a raw value, treating empty/absent as no value."""

    if raw is None or raw == "":
        return None
    value = converter(raw)
    return None if value == [] else value


def _peer_status(data: dict[str, Any]) -> dict[int, ARVpnState]:
    """Map peer index -> live state from the status hook."""

    status: dict[int, ARVpnState] = {}
    hook = data.get(HOOK.value)
    if not isinstance(hook, dict):
        return status

    for entry in hook.get("client_status", []):
        index = raw_to_int(entry.get("index"))
        if index is None:
            continue
        state = raw_to_int(entry.get("status"))
        status[index] = (
            ARVpnState.CONNECTED if state == 1 else ARVpnState.DISCONNECTED
        )

    return status


def _peer(
    data: dict[str, Any], index: int, status: dict[int, ARVpnState]
) -> dict[ARVpnPeerField, Any] | None:
    """Build a single peer entry, or None when the slot is empty."""

    fields: dict[ARVpnPeerField, Any] = {}
    for kind, field, converter in _PEER:
        value = _convert(data.get(kind.key(index)), converter)
        if value is not None:
            fields[field] = value

    if not fields:
        return None

    if index in status:
        fields[ARVpnPeerField.STATE] = status[index]

    return fields


def translate(data: dict[str, Any]) -> dict[int, dict[ARVpnServerField, Any]]:
    """Translate raw data into the WireGuard server profile keyed by unit."""

    fields: dict[ARVpnServerField, Any] = {}
    for key, field, converter in _SETTINGS:
        value = _convert(data.get(key.value), converter)
        if value is not None:
            fields[field] = value

    if not fields:
        return {}

    status = _peer_status(data)
    peers = [
        peer
        for index in range(1, MAX_PEERS + 1)
        if (peer := _peer(data, index, status)) is not None
    ]
    if peers:
        fields[ARVpnServerField.CLIENTS] = peers

    return {UNIT: fields}
