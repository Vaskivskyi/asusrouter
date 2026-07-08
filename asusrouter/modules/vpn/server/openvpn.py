"""OpenVPN server backend for the VPN module."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from asusrouter.modules.common.command import ARService
from asusrouter.modules.firmware import (
    AR_FW_388,
    AR_FW_MERLIN_LIKE,
    ARFirmwareType,
)
from asusrouter.modules.vpn.enums import (
    ARVpnClientField,
    ARVpnServerField,
    ARVpnState,
)
from asusrouter.tools.converters_v2.raw import (
    raw_to_bool,
    raw_to_int,
    raw_to_str,
)
from asusrouter.tools.identifiers import IpAddress, IpInterface, Password

if TYPE_CHECKING:
    from asusrouter.modules.device.identity import ARDeviceIdentity
    from asusrouter.modules.service.action import ARServiceInput

# OpenVPN server units exposed by the firmware
UNITS = (1, 2)

# Key under which the source stashes the connected-client status
CLIENT_STATUS_KEY = "_openvpn_client_status"

# Settings nvram key -> field, converter (apply to the active unit only)
_SETTINGS: tuple[tuple[str, ARVpnServerField, Callable[[Any], Any]], ...] = (
    ("vpn_server_port", ARVpnServerField.PORT, raw_to_int),
    ("vpn_server_proto", ARVpnServerField.PROTOCOL, raw_to_str),
    ("vpn_server_if", ARVpnServerField.INTERFACE, raw_to_str),
    ("vpn_server_crypt", ARVpnServerField.CRYPT, raw_to_str),
    ("vpn_server_cipher", ARVpnServerField.CIPHER, raw_to_str),
    ("vpn_server_digest", ARVpnServerField.DIGEST, raw_to_str),
    ("vpn_server_comp", ARVpnServerField.COMPRESSION, raw_to_str),
    ("vpn_server_hmac", ARVpnServerField.HMAC, raw_to_int),
    ("vpn_server_tls_keysize", ARVpnServerField.TLS_KEYSIZE, raw_to_int),
    ("vpn_server_igncrt", ARVpnServerField.IGNORE_CERTIFICATE, raw_to_bool),
    ("vpn_server_pdns", ARVpnServerField.PUSH_DNS, raw_to_bool),
    ("vpn_server_sn", ARVpnServerField.SUBNET, IpAddress.from_value_safe),
    ("vpn_server_nm", ARVpnServerField.NETMASK, IpAddress.from_value_safe),
    ("vpn_server_dhcp", ARVpnServerField.DHCP, raw_to_bool),
    ("vpn_server_r1", ARVpnServerField.POOL_START, IpAddress.from_value_safe),
    ("vpn_server_r2", ARVpnServerField.POOL_END, IpAddress.from_value_safe),
    (
        "vpn_server_local",
        ARVpnServerField.LOCAL_ADDRESS,
        IpAddress.from_value_safe,
    ),
    (
        "vpn_server_remote",
        ARVpnServerField.REMOTE_ADDRESS,
        IpAddress.from_value_safe,
    ),
    ("vpn_server_reneg", ARVpnServerField.RENEG, raw_to_int),
    ("vpn_server_rgw", ARVpnServerField.REDIRECT_GATEWAY, raw_to_int),
    ("vpn_server_c2c", ARVpnServerField.CLIENT_TO_CLIENT, raw_to_bool),
)


def server_enabled(data: dict[str, Any]) -> bool:
    """Whether the OpenVPN server is enabled (worth fetching live status)."""

    return raw_to_bool(data.get("VPNServer_enable")) is True


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
    arguments: dict[str, Any] = {"VPNServer_enable": int(state), "id": unit}
    return services, arguments


def nvram_keys() -> list[str]:
    """Return the nvram keys required to read every OpenVPN server unit."""

    keys = ["VPNServer_enable", "vpn_server_unit", "vpn_serverx_clientlist"]
    keys.extend(key for key, _, _ in _SETTINGS)
    for unit in UNITS:
        keys.append(f"vpn_server{unit}_state")
        keys.append(f"vpn_server{unit}_errno")
    return keys


def _convert(raw: Any, converter: Callable[[Any], Any]) -> Any:
    """Convert a raw value, treating empty/absent as no value."""

    if raw is None or raw == "":
        return None
    return converter(raw)


def _settings(data: dict[str, Any]) -> dict[ARVpnServerField, Any]:
    """Read the active-unit settings block."""

    fields: dict[ARVpnServerField, Any] = {}
    for key, field, converter in _SETTINGS:
        value = _convert(data.get(key), converter)
        if value is not None:
            fields[field] = value
    return fields


def _clients(raw: Any) -> list[dict[ARVpnClientField, Any]]:
    """Parse the `<username>password` account list of the active unit."""

    text = raw_to_str(raw)
    if text is None:
        return []
    # nvram may HTML-encode the `<` / `>` delimiters
    text = text.replace("&#60", "<").replace("&#62", ">")

    clients: list[dict[ARVpnClientField, Any]] = []
    for entry in text.split("<"):
        parts = entry.split(">")
        name = raw_to_str(parts[0])
        if name is None:
            continue
        client: dict[ARVpnClientField, Any] = {ARVpnClientField.NAME: name}
        raw_password = parts[1] if len(parts) > 1 else None
        password = Password.from_value_safe(raw_password)
        if password is not None:
            client[ARVpnClientField.PASSWORD] = password
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


def _live_fields(entry: dict[str, Any]) -> dict[ARVpnClientField, Any]:
    """Build the live fields (state, address, remote) of a connected client."""

    fields: dict[ARVpnClientField, Any] = {
        ARVpnClientField.STATE: ARVpnState.CONNECTED
    }

    address = IpInterface.from_value_safe(entry.get("vpn_ip"))
    if address is not None:
        fields[ARVpnClientField.ADDRESS] = [address]

    remote = raw_to_str(entry.get("remote"))
    if remote is not None:
        host, sep, port = remote.rpartition(":")
        remote_ip = IpAddress.from_value_safe(host if sep else remote)
        if remote_ip is not None:
            fields[ARVpnClientField.REMOTE_ADDRESS] = remote_ip
        remote_port = raw_to_int(port) if sep else None
        if remote_port is not None:
            fields[ARVpnClientField.REMOTE_PORT] = remote_port

    return fields


def _apply_status(
    clients: list[dict[ARVpnClientField, Any]],
    connected: dict[str, dict[str, Any]],
) -> list[dict[ARVpnClientField, Any]]:
    """Enrich connected accounts, and add connected clients not in the list."""

    for client in clients:
        name = client.get(ARVpnClientField.NAME)
        entry = connected.get(name) if isinstance(name, str) else None
        if entry is not None:
            client.update(_live_fields(entry))

    listed = {client.get(ARVpnClientField.NAME) for client in clients}
    clients.extend(
        {ARVpnClientField.NAME: name, **_live_fields(entry)}
        for name, entry in sorted(connected.items())
        if name not in listed
    )

    return clients


def translate(data: dict[str, Any]) -> dict[int, dict[ARVpnServerField, Any]]:
    """Translate raw data into OpenVPN server profiles keyed by unit."""

    active = raw_to_int(data.get("vpn_server_unit"))
    enabled = raw_to_bool(data.get("VPNServer_enable"))
    settings = _settings(data)

    result: dict[int, dict[ARVpnServerField, Any]] = {}
    for unit in UNITS:
        fields: dict[ARVpnServerField, Any] = {}

        state = _convert(
            data.get(f"vpn_server{unit}_state"), ARVpnState.from_value
        )
        if state is not None:
            fields[ARVpnServerField.STATE] = state
        errno = _convert(data.get(f"vpn_server{unit}_errno"), raw_to_int)
        if errno is not None:
            fields[ARVpnServerField.ERRNO] = errno

        # Settings, accounts and the enable flag belong to the active unit
        if unit == active:
            if enabled is not None:
                fields[ARVpnServerField.ENABLED] = enabled
            fields.update(settings)
            clients = _apply_status(
                _clients(data.get("vpn_serverx_clientlist")),
                _connected(data),
            )
            if clients:
                fields[ARVpnServerField.CLIENTS] = clients

        if fields:
            result[unit] = fields

    return result
