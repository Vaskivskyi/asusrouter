"""Hook endpoint module."""

from __future__ import annotations

import logging
from typing import Any

from asusrouter.modules.aura import process_aura
from asusrouter.modules.common.connection import ARConnectionState
from asusrouter.modules.data import AsusData
from asusrouter.modules.ddns import process_ddns
from asusrouter.modules.endpoint.error import AccessError
from asusrouter.modules.led import AsusLED
from asusrouter.modules.parental_control import (
    KEY_PC_BLOCK_ALL,
    KEY_PC_STATE,
    AsusBlockAll,
    AsusParentalControl,
    read_pc_rules,
)
from asusrouter.modules.port_forwarding import (
    KEY_PORT_FORWARDING_LIST,
    KEY_PORT_FORWARDING_STATE,
    AsusPortForwarding,
    PortForwardingRule,
)
from asusrouter.modules.vpnc import AsusVPNC, AsusVPNType
from asusrouter.tools.converters import run_method, safe_unpack_keys
from asusrouter.tools.converters_v2.raw import (
    raw_to_bool,
    raw_to_int,
    raw_to_str,
)
from asusrouter.tools.readers import merge_dicts

from .hook_const import (
    MAP_OVPN_SERVER_388,
    MAP_VPNC_WIREGUARD,
    MAP_WIREGUARD_CLIENT,
    MAP_WIREGUARD_SERVER,
)

_LOGGER = logging.getLogger(__name__)

_VPNC_PART_MIN_FIELDS = 7


def process(data: dict[str, Any]) -> dict[AsusData, Any]:  # noqa: C901, PLR0912
    """Process hook data."""

    # For this endpoint, the received data always depends on the sent request.
    # So, we need to check which data is available and process it accordingly.
    # Otherwise, we can accidentally overwrite the data with empty values.

    state: dict[AsusData, Any] = {}

    # Aura
    if "ledg_scheme" in data:
        state[AsusData.AURA] = process_aura(data)

    # DDNS
    if (
        "ddns_return_code_chk" in data
        or "ddns_server_x" in data
        or "ddns_hostname_x" in data
    ):
        state[AsusData.DDNS] = process_ddns(data)

    # LED
    if "led_val" in data:
        _led = raw_to_int(data.get("led_val"))
        state[AsusData.LED] = {
            "state": AsusLED(_led if _led is not None else -999)
        }

    # OpenVPN Server
    if "vpn_serverx_clientlist" in data:
        state[AsusData.OPENVPN_SERVER] = process_openvpn_server(data)

    # Parental control
    if KEY_PC_STATE in data:
        state[AsusData.PARENTAL_CONTROL] = process_parental_control(data)

    # Port forwarding
    if KEY_PORT_FORWARDING_STATE in data:
        state[AsusData.PORT_FORWARDING] = process_port_forwarding(data)

    # VPNC
    if "vpnc_clientlist" in data:
        vpnc, vpnc_clientlist = process_vpnc(data)
        state[AsusData.OPENVPN_CLIENT] = vpnc[AsusVPNType.OPENVPN]
        state[AsusData.VPNC] = vpnc
        state[AsusData.VPNC_CLIENTLIST] = vpnc_clientlist
        state[AsusData.WIREGUARD_CLIENT] = vpnc[AsusVPNType.WIREGUARD]

    # WireGuard
    if "get_wgsc_status" in data:
        state[AsusData.WIREGUARD_SERVER] = process_wireguard_server(data)

    # DSL
    if "dsllog_dataratedown" in data or "dsllog_datarateup" in data:
        state[AsusData.DSL] = process_dsl(data)

    return state


def process_openvpn_server(data: dict[str, Any]) -> dict[int, Any]:
    """Process OpenVPN server data."""

    server = {}

    # Server data
    for keys in MAP_OVPN_SERVER_388:
        key, key_to_use, method = safe_unpack_keys(keys)
        state_value = data.get(key)
        if state_value:
            server[key_to_use] = run_method(state_value, method)

    # Clients
    clients = server.get("clients", "")
    clients = clients.replace("&#62", ">").replace("&#60", "<")
    clients = clients[1:-1].split("><")
    server["clients"] = clients

    return {1: server}


def process_parental_control(data: dict[str, Any]) -> dict[str, Any]:
    """Process parental control data."""

    parental_control: dict[str, Any] = {}

    # State
    parental_control["state"] = AsusParentalControl(
        _v if (_v := raw_to_int(data.get(KEY_PC_STATE))) is not None else -999
    )

    # Block all
    _block_all = raw_to_int(data.get(KEY_PC_BLOCK_ALL))
    parental_control["block_all"] = AsusBlockAll(
        _block_all if _block_all is not None else -999
    )

    # Rules
    parental_control["rules"] = read_pc_rules(data)

    return parental_control


def process_port_forwarding(data: dict[str, Any]) -> dict[str, Any]:
    """Process port forwarding data."""

    port_forwarding = {}

    # State
    port_forwarding["state"] = AsusPortForwarding(
        _v
        if (_v := raw_to_int(data.get(KEY_PORT_FORWARDING_STATE))) is not None
        else -999
    )

    # Rules
    pf_list = data.get(KEY_PORT_FORWARDING_LIST)
    if pf_list:
        rules = []
        rule_list = pf_list.split("&#60")
        for rule in rule_list:
            if rule == "":
                continue
            part = rule.split("&#62")
            rules.append(
                PortForwardingRule(
                    name=raw_to_str(part[0]),
                    ip_address=part[2],
                    port=raw_to_str(part[3]),
                    protocol=part[4],
                    ip_external=raw_to_str(part[5]),
                    port_external=part[1],
                )
            )
        port_forwarding["rules"] = rules.copy()

    return port_forwarding


def process_vpnc(  # noqa: C901
    data: dict[str, Any],
) -> tuple[dict[AsusVPNType, dict[int, Any]], str]:
    """Process VPNC data."""

    vpnc = {}

    # Get client list
    vpnc_clientlist = (
        data.get("vpnc_clientlist", "")
        .replace("&#62", ">")
        .replace("&#60", "<")
    )
    if vpnc_clientlist != "":
        clients = vpnc_clientlist.split("<")
        vpnc_unit = 0
        for client in clients:
            if client == "":
                continue
            part = client.split(">")
            # Format: name, type, id, login, password, active,
            #         vpnc_id, ?, ?, ?, ?, `Web`
            if len(part) < _VPNC_PART_MIN_FIELDS:
                continue
            vpnc_id = raw_to_int(part[6])
            vpnc[vpnc_id] = {
                "type": (
                    AsusVPNType(part[1])
                    if part[1] in [e.value for e in AsusVPNType]
                    else AsusVPNType.UNKNOWN
                ),
                "id": raw_to_int(part[2]),
                "name": raw_to_str(part[0]),
                "login": raw_to_str(part[3]),
                "password": raw_to_str(part[4]),
                "active": raw_to_bool(part[5]),
                "vpnc_unit": vpnc_unit,
            }
            vpnc_unit += 1

    # Get clients status
    get_vpnc_status = data.get("get_vpnc_status")
    if get_vpnc_status:
        clients = get_vpnc_status.split("<")
        for client in clients:
            if client == "":
                continue
            part = client.split(">")
            vpnc_id = raw_to_int(part[2])
            state_code = raw_to_int(part[0])
            error_code = raw_to_int(part[1])
            vpnc[vpnc_id].update(
                {
                    "state": (
                        AsusVPNC(state_code)
                        if state_code in [e.value for e in AsusVPNC]
                        else AsusVPNC.UNKNOWN
                    ),
                    "error": (
                        AccessError(error_code)
                        if error_code in [e.value for e in AccessError]
                        else AccessError.UNKNOWN
                    ),
                }
            )

    # Re-sort the data by VPN type / id
    vpn: dict[AsusVPNType, dict[int, Any]] = {
        AsusVPNType.L2TP: {},
        AsusVPNType.OPENVPN: {},
        AsusVPNType.PPTP: {},
        AsusVPNType.SURFSHARK: {},
        AsusVPNType.WIREGUARD: {},
        AsusVPNType.UNKNOWN: {},
    }

    for vpnc_id, info in vpnc.items():
        sorted_id = info.pop("id", None)
        sorted_type = info.pop("type", None)
        info["vpnc_id"] = vpnc_id
        vpn[sorted_type][sorted_id] = info

    # Process WireGuard data
    vpn[AsusVPNType.WIREGUARD] = merge_dicts(
        vpn[AsusVPNType.WIREGUARD], process_vpnc_wireguard(data)
    )
    # Fill missing clients with unknown state
    for num in range(1, 6):
        if num not in vpn[AsusVPNType.WIREGUARD]:
            vpn[AsusVPNType.WIREGUARD][num] = {
                "state": AsusVPNC.UNKNOWN,
                "error": AccessError.NO_ERROR,
            }
        if num not in vpn[AsusVPNType.OPENVPN]:
            vpn[AsusVPNType.OPENVPN][num] = {
                "state": AsusVPNC.UNKNOWN,
                "error": AccessError.NO_ERROR,
            }

    # Remove UNKNOWN VPN type if it's empty
    if not vpn[AsusVPNType.UNKNOWN]:
        vpn.pop(AsusVPNType.UNKNOWN, None)

    return vpn, vpnc_clientlist


def process_vpnc_wireguard(data: dict[str, Any]) -> dict[int, dict[str, Any]]:
    """Process VPNC WireGuard data."""

    wireguard = {}

    for num in range(1, 6):
        client = {}
        for keys in MAP_VPNC_WIREGUARD:
            key, key_to_use, method = safe_unpack_keys(keys)
            state_value = data.get(f"wgc{num}_{key}")
            if state_value:
                client[key_to_use] = run_method(state_value, method)
        if client:
            wireguard[num] = client

    return wireguard


def process_wireguard_server(  # noqa: C901
    data: dict[str, Any],
) -> dict[int, dict[str, Any]]:
    """Process WireGuard data."""

    wireguard = {}

    # Server data
    for keys in MAP_WIREGUARD_SERVER:
        key, key_to_use, method = safe_unpack_keys(keys)
        state_value = data.get(key)
        if state_value:
            wireguard[key_to_use] = run_method(state_value, method)

    # Per-client data
    wireguard["clients"] = {}
    for num in range(1, 11):
        client = {}
        for keys in MAP_WIREGUARD_CLIENT:
            key, key_to_use, method = safe_unpack_keys(keys)
            state_value = data.get(f"wgs1_c{num}_{key}")
            if state_value:
                client[key_to_use] = run_method(state_value, method)
        if client:
            wireguard["clients"][num] = client

    if "status" in wireguard:
        status = wireguard["status"].get("client_status")
        if status:
            for client in status:
                if client.get("index") in wireguard["clients"]:
                    wireguard["clients"][client.get("index")]["state"] = (
                        ARConnectionState.from_value(client.get("status"))
                    )

    # Remove the `status` value
    wireguard.pop("status", None)

    return {1: wireguard}


def process_dsl(dsl_info: dict[str, Any]) -> dict[str, Any]:
    """Process DSL data."""

    def remove_units(value: str | None) -> str | None:
        """Remove units from the value."""

        if value is None:
            return None
        return value.split(" ")[0]

    dsl: dict[str, Any] = {}

    # Data preprocessing
    _dataratedown = remove_units(dsl_info.get("dsllog_dataratedown"))
    _datarateup = remove_units(dsl_info.get("dsllog_datarateup"))

    dsl["datarate"] = {
        "down": raw_to_int(_dataratedown) or 0,
        "up": raw_to_int(_datarateup) or 0,
    }

    return dsl
