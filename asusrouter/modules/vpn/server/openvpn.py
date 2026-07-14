"""OpenVPN server backend for the VPN module."""

from __future__ import annotations

from collections.abc import Callable
import re
from typing import TYPE_CHECKING, Any

from asusrouter.modules.common.command import ARService
from asusrouter.modules.firmware import (
    AR_FW_388,
    AR_FW_MERLIN_LIKE,
    ARFirmwareType,
)
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
    raw_convert,
    raw_to_bool,
    raw_to_int,
    raw_to_str,
)
from asusrouter.tools.identifiers import IpAddress, IpInterface, Password
from asusrouter.tools.readers_v2.nvram_list import get_field, split_rows
from asusrouter.tools.readers_v2.table import read_table

if TYPE_CHECKING:
    from asusrouter.modules.device.identity import ARDeviceIdentity
    from asusrouter.modules.service.action import ARServiceInput

# OpenVPN server units exposed by the firmware
UNITS = (1, 2)

# Key under which the source stashes the connected-client status
CLIENT_STATUS_KEY = "_openvpn_client_status"

# Settings nvram key -> field, converter (apply to the active unit only)
_SETTINGS: tuple[
    tuple[ARNvramType, ARVpnServerField, Callable[[Any], Any]], ...
] = (
    (ARNvramType.VPN_SERVER_PORT, ARVpnServerField.PORT, raw_to_int),
    (ARNvramType.VPN_SERVER_PROTO, ARVpnServerField.PROTOCOL, raw_to_str),
    (ARNvramType.VPN_SERVER_IF, ARVpnServerField.INTERFACE, raw_to_str),
    (ARNvramType.VPN_SERVER_CRYPT, ARVpnServerField.CRYPT, raw_to_str),
    (ARNvramType.VPN_SERVER_CIPHER, ARVpnServerField.CIPHER, raw_to_str),
    (ARNvramType.VPN_SERVER_DIGEST, ARVpnServerField.DIGEST, raw_to_str),
    (ARNvramType.VPN_SERVER_COMP, ARVpnServerField.COMPRESSION, raw_to_str),
    (ARNvramType.VPN_SERVER_HMAC, ARVpnServerField.HMAC, raw_to_int),
    (
        ARNvramType.VPN_SERVER_TLS_KEYSIZE,
        ARVpnServerField.TLS_KEYSIZE,
        raw_to_int,
    ),
    (
        ARNvramType.VPN_SERVER_IGNCRT,
        ARVpnServerField.IGNORE_CERTIFICATE,
        raw_to_bool,
    ),
    (ARNvramType.VPN_SERVER_PDNS, ARVpnServerField.PUSH_DNS, raw_to_bool),
    (
        ARNvramType.VPN_SERVER_SN,
        ARVpnServerField.SUBNET,
        IpAddress.from_value_safe,
    ),
    (
        ARNvramType.VPN_SERVER_NM,
        ARVpnServerField.NETMASK,
        IpAddress.from_value_safe,
    ),
    (ARNvramType.VPN_SERVER_DHCP, ARVpnServerField.DHCP, raw_to_bool),
    (
        ARNvramType.VPN_SERVER_R1,
        ARVpnServerField.POOL_START,
        IpAddress.from_value_safe,
    ),
    (
        ARNvramType.VPN_SERVER_R2,
        ARVpnServerField.POOL_END,
        IpAddress.from_value_safe,
    ),
    (
        ARNvramType.VPN_SERVER_LOCAL,
        ARVpnServerField.LOCAL_ADDRESS,
        IpAddress.from_value_safe,
    ),
    (
        ARNvramType.VPN_SERVER_REMOTE,
        ARVpnServerField.REMOTE_ADDRESS,
        IpAddress.from_value_safe,
    ),
    (ARNvramType.VPN_SERVER_RENEG, ARVpnServerField.RENEG, raw_to_int),
    (
        ARNvramType.VPN_SERVER_RGW,
        ARVpnServerField.REDIRECT_GATEWAY,
        raw_to_int,
    ),
    (
        ARNvramType.VPN_SERVER_C2C,
        ARVpnServerField.CLIENT_TO_CLIENT,
        raw_to_bool,
    ),
)


def server_enabled(data: dict[str, Any]) -> bool:
    """Whether the OpenVPN server is enabled (worth fetching live status)."""

    return raw_to_bool(data.get(ARNvramType.VPN_SERVER_ENABLE.value)) is True


# A connected-client status line: `remote_ip:port vpn_ip name`
_STATUS_FIELDS = 3


def read_client_status(content: str | None) -> dict[str, Any]:
    """Parse the connected-client status payload of the OpenVPN server.

    The payload wraps plaintext lines in a `<vpnserver>` tag; each line is
    `remote_ip:port vpn_ip name`.
    """

    content = raw_to_str(content)
    if not content:
        return {}

    match = re.search(r"<vpnserver>(.*?)</vpnserver>", content, re.DOTALL)
    body = match[1] if match else content

    connected: list[dict[str, str]] = []
    for line in body.splitlines():
        fields = line.split()
        if len(fields) != _STATUS_FIELDS:
            continue
        remote, vpn_ip, name = fields
        connected.append({"name": name, "vpn_ip": vpn_ip, "remote": remote})

    return {"connected": connected}


def _is_legacy(identity: ARDeviceIdentity | None) -> bool:
    """Whether the firmware uses the legacy per-unit start/stop services."""

    if identity is None:
        return True
    firmware = identity.firmware
    return (
        firmware.firmware_type in AR_FW_MERLIN_LIKE
        or firmware.firmware_type != ARFirmwareType.STOCK
        or firmware < AR_FW_388
    )


def build_toggle_payload(
    unit: int, state: bool, identity: ARDeviceIdentity | None
) -> tuple[list[ARServiceInput], dict[str, Any]]:
    """Build `(services, arguments)` to enable/disable the OpenVPN server."""

    if _is_legacy(identity):
        service = (
            f"start_vpnserver{unit}" if state else f"stop_vpnserver{unit}"
        )
        return [service], {"id": unit}

    services: list[ARServiceInput] = (
        [
            ARService.OPENVPN_RESTART,
            ARService.CHPASS_RESTART,
            ARService.SAMBA_RESTART,
            ARService.DNS_RESTART,
        ]
        if state
        else [
            ARService.OPENVPN_STOP,
            ARService.SAMBA_RESTART,
            ARService.DNS_RESTART,
        ]
    )
    arguments: dict[str, Any] = {
        ARNvramType.VPN_SERVER_ENABLE.value: int(state),
        "id": unit,
    }
    return services, arguments


def nvram_items() -> list[ARNvramItem]:
    """Return the nvram items required to read every OpenVPN server unit."""

    items: list[ARNvramItem] = [
        ARNvramType.VPN_SERVER_ENABLE,
        ARNvramType.VPN_SERVER_UNIT,
        ARNvramType.VPN_SERVER_CLIENTLIST,
    ]
    items.extend(key for key, _, _ in _SETTINGS)
    for unit in UNITS:
        items.append(
            ARNvramIndexSource(ARNvramIndexType.VPN_SERVER_STATE, unit)
        )
        items.append(
            ARNvramIndexSource(ARNvramIndexType.VPN_SERVER_ERRNO, unit)
        )
    return items


def _settings(data: dict[str, Any]) -> dict[ARVpnServerField, Any]:
    """Read the active-unit settings block."""

    return read_table(data, _SETTINGS)


def _clients(raw: Any) -> list[dict[ARVpnPeerField, Any]]:
    """Parse the `<username>password` account list of the active unit."""

    clients: list[dict[ARVpnPeerField, Any]] = []
    for entry in split_rows(raw):
        parts = entry.split(">")
        name = raw_to_str(parts[0])
        if name is None:
            continue
        client: dict[ARVpnPeerField, Any] = {ARVpnPeerField.NAME: name}
        password = Password.from_value_safe(get_field(parts, 1))
        if password is not None:
            client[ARVpnPeerField.PASSWORD] = password
        clients.append(client)

    return clients


def _connected(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Map client name -> its live connection entry from the status."""

    status = data.get(CLIENT_STATUS_KEY)
    if not isinstance(status, dict):
        return {}

    result: dict[str, dict[str, Any]] = {}
    for entry in status.get("connected", []):
        name = raw_to_str(entry.get("name"))
        if name is not None:
            result[name] = entry
    return result


def _live_fields(entry: dict[str, Any]) -> dict[ARVpnPeerField, Any]:
    """Build the live fields (state, address, remote) of a connected client."""

    fields: dict[ARVpnPeerField, Any] = {
        ARVpnPeerField.STATE: ARVpnState.CONNECTED
    }

    address = IpInterface.from_value_safe(entry.get("vpn_ip"))
    if address is not None:
        fields[ARVpnPeerField.ADDRESS] = [address]

    remote = raw_to_str(entry.get("remote"))
    if remote is not None:
        host, sep, port = remote.rpartition(":")
        remote_ip = IpAddress.from_value_safe(host if sep else remote)
        if remote_ip is not None:
            fields[ARVpnPeerField.REMOTE_ADDRESS] = remote_ip
        remote_port = raw_to_int(port) if sep else None
        if remote_port is not None:
            fields[ARVpnPeerField.REMOTE_PORT] = remote_port

    return fields


def _apply_status(
    clients: list[dict[ARVpnPeerField, Any]],
    connected: dict[str, dict[str, Any]],
) -> list[dict[ARVpnPeerField, Any]]:
    """Enrich connected accounts, and add connected clients not in the list."""

    for client in clients:
        name = client.get(ARVpnPeerField.NAME)
        entry = connected.get(name) if isinstance(name, str) else None
        if entry is not None:
            client.update(_live_fields(entry))

    listed = {client.get(ARVpnPeerField.NAME) for client in clients}
    clients.extend(
        {ARVpnPeerField.NAME: name, **_live_fields(entry)}
        for name, entry in sorted(connected.items())
        if name not in listed
    )

    return clients


def translate(data: dict[str, Any]) -> dict[int, dict[ARVpnServerField, Any]]:
    """Translate raw data into OpenVPN server profiles keyed by unit."""

    active = raw_to_int(data.get(ARNvramType.VPN_SERVER_UNIT.value))
    enabled = raw_to_bool(data.get(ARNvramType.VPN_SERVER_ENABLE.value))
    settings = _settings(data)

    result: dict[int, dict[ARVpnServerField, Any]] = {}
    for unit in UNITS:
        fields: dict[ARVpnServerField, Any] = {}

        state = raw_convert(
            data.get(ARNvramIndexType.VPN_SERVER_STATE.key(unit)),
            ARVpnState.from_value,
        )
        if state is not None:
            fields[ARVpnServerField.STATE] = state
        errno = raw_convert(
            data.get(ARNvramIndexType.VPN_SERVER_ERRNO.key(unit)), raw_to_int
        )
        if errno is not None:
            fields[ARVpnServerField.ERRNO] = errno

        # Settings, accounts and the enable flag belong to the active unit
        if unit == active:
            if enabled is not None:
                fields[ARVpnServerField.ENABLED] = enabled
            fields.update(settings)
            clients = _apply_status(
                _clients(data.get(ARNvramType.VPN_SERVER_CLIENTLIST.value)),
                _connected(data),
            )
            if clients:
                fields[ARVpnServerField.CLIENTS] = clients

        if fields:
            result[unit] = fields

    return result
