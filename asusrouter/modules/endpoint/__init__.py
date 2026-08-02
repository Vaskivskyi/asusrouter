"""Endpoint module for AsusRouter."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
import json
from typing import Any

from asusrouter.const import UNKNOWN_MEMBER_STR, RequestType
from asusrouter.modules.common.command import ACTION_MODE_KEY, ARActionMode
from asusrouter.modules.endpoint.translate import read_wan_lan_status
from asusrouter.tools.converters.raw import raw_to_str
from asusrouter.tools.enum import FromStrMixin
from asusrouter.tools.readers import (
    read_js_variables,
    read_json_content,
    read_netdev,
)
from asusrouter.tools.security import ARSecurityLevel


class AREndpoint(FromStrMixin, StrEnum):
    """Endpoint enum.

    Values are the URL paths used to communicate with the device.
    """

    UNKNOWN = UNKNOWN_MEMBER_STR

    # Read endpoints
    FETCH_CLIENTS_UPDATE = "update_clients.asp"
    FETCH_DATA = "appGet.cgi"
    FETCH_DEVICEMAP = "ajax_status.xml"
    FETCH_DIAGNOSTICS_ACTIVE_CLIENT = "get_diag_active_client.cgi"
    FETCH_DIAGNOSTICS_DATA = "get_diag_content_data.cgi"
    FETCH_FIRMWARE_UPDATE = "detect_firmware.asp"
    FETCH_FIRMWARE_UPDATE_NOTE = "release_note0.asp"
    FETCH_FIRMWARE_UPDATE_NOTE_AIMESH = "release_note_amas.asp"
    FETCH_LOG = "ajax_log_data.asp"
    FETCH_NETWORK = "netool.cgi"
    FETCH_ONBOARDING = "ajax_onboarding.asp"
    FETCH_PORT_STATUS = "get_port_status.cgi"
    FETCH_PORTS_ETHERNET = "ajax_ethernet_ports.asp"
    FETCH_SYSINFO = "ajax_sysinfo.asp"
    FETCH_TEMPERATURE = "ajax_coretmp.asp"
    FETCH_TRAFFIC_BACKHAUL = "get_diag_sta_traffic.cgi"
    FETCH_TRAFFIC_ETHERNET = "get_diag_eth_traffic.cgi"
    FETCH_TRAFFIC_WIFI = "get_diag_wifi_traffic.cgi"
    FETCH_UPDATE = "update.cgi"
    FETCH_VPN_OPENVPN_STATUS = "ajax_openvpn_client_status.xml"
    FETCH_VPN_STATUS = "ajax_vpn_status.asp"

    # Write endpoints
    CHPASS = "chpass.cgi"
    DDNS_CLEAN = "clean_ddns.cgi"
    DDNS_UNREGISTER = "unreg_ASUSDDNS.cgi"
    PUSH_DATA = "applyapp.cgi"
    RUN_PING = "dns_ping.cgi"
    RUN_SPEEDTEST = "ookla_speedtest_exe.cgi"
    SET_AURA = "set_ledg.cgi"
    SET_SPEEDTEST_START_TIME = "set_ookla_speedtest_start_time.cgi"
    START_APPLY = "start_apply.htm"
    WRITE_SPEEDTEST_HISTORY = "ookla_speedtest_write_history.cgi"

    # Service endpoints
    LOGIN = "login.cgi"
    LOGOUT = "Logout.asp"


# Endpoints not yet implemented
#     # Control endpoints
#     APPLY = "apply.cgi"

# Known endpoints, currently unused
#     CERT_INFO = "ajax_certinfo.asp"
#     DDNS_CODE = "ajax_ddnscode.asp"
#     DSL = "ajax_AdslStatus.asp"
#     NETWORKMAPD = "update_networkmapd.asp"
#     STATE = "state.js"


@dataclass
class AREndpointMeta:
    """Metadata for an AREndpoint."""

    request_type: RequestType = RequestType.POST
    # Minimum log security level at which the request payload may be logged
    # raw; below it the payload is redacted
    payload_sensitivity: ARSecurityLevel = ARSecurityLevel.DEFAULT
    raw_payload: bool = False


_DEFAULT_META = AREndpointMeta()
_GET_META = AREndpointMeta(request_type=RequestType.GET)
_RAW_POST_META = AREndpointMeta(raw_payload=True)
# Raw POST whose body carries user data (e.g. real IPs) - never log by default
_RAW_POST_SENSITIVE_META = AREndpointMeta(
    raw_payload=True, payload_sensitivity=ARSecurityLevel.UNSAFE
)

_ENDPOINT_META: dict[AREndpoint, AREndpointMeta] = {
    AREndpoint.CHPASS: _RAW_POST_SENSITIVE_META,
    AREndpoint.DDNS_CLEAN: _GET_META,
    AREndpoint.DDNS_UNREGISTER: _GET_META,
    AREndpoint.FETCH_DIAGNOSTICS_ACTIVE_CLIENT: _GET_META,
    AREndpoint.FETCH_DIAGNOSTICS_DATA: _GET_META,
    AREndpoint.FETCH_NETWORK: _GET_META,
    AREndpoint.FETCH_PORT_STATUS: _GET_META,
    AREndpoint.FETCH_TRAFFIC_BACKHAUL: _GET_META,
    AREndpoint.FETCH_TRAFFIC_ETHERNET: _GET_META,
    AREndpoint.FETCH_TRAFFIC_WIFI: _GET_META,
    AREndpoint.FETCH_UPDATE: _GET_META,
    AREndpoint.FETCH_VPN_OPENVPN_STATUS: _GET_META,
    AREndpoint.FETCH_VPN_STATUS: _GET_META,
    AREndpoint.RUN_PING: _GET_META,
    AREndpoint.RUN_SPEEDTEST: _RAW_POST_META,
    AREndpoint.SET_AURA: _GET_META,
    AREndpoint.SET_SPEEDTEST_START_TIME: _RAW_POST_META,
    # Might contain sensitive data, including passwords
    AREndpoint.START_APPLY: _RAW_POST_SENSITIVE_META,
    AREndpoint.WRITE_SPEEDTEST_HISTORY: _RAW_POST_SENSITIVE_META,
    AREndpoint.LOGIN: AREndpointMeta(
        payload_sensitivity=ARSecurityLevel.UNSAFE
    ),
}


def get_endpoint_meta(endpoint: AREndpoint) -> AREndpointMeta:
    """Get metadata for the given endpoint."""

    return _ENDPOINT_META.get(endpoint, _DEFAULT_META)


def get_endpoint_request_type(endpoint: AREndpoint) -> RequestType:
    """Get the request type for the given endpoint."""

    return get_endpoint_meta(endpoint).request_type


def get_endpoint_payload_sensitivity(endpoint: AREndpoint) -> ARSecurityLevel:
    """Get the payload log sensitivity for the given endpoint."""

    return get_endpoint_meta(endpoint).payload_sensitivity


def get_endpoint_raw_payload(endpoint: AREndpoint) -> bool:
    """Check if the endpoint's POST body must be sent verbatim."""

    return get_endpoint_meta(endpoint).raw_payload


def build_push_request(
    action_mode: ARActionMode | str = ARActionMode.APPLY,
    payload: Mapping[str, Any] | None = None,
) -> str:
    """Build a PUSH_DATA (applyapp.cgi) request body.

    The endpoint expects a compact JSON object with an `action_mode` and
    optional command fields; the connection URL-encodes it on the wire.
    """

    commands: dict[str, Any] = {ACTION_MODE_KEY: str(action_mode)}
    if payload:
        commands.update(payload)
    return json.dumps(commands, separators=(",", ":"))


_ENDPOINT_READER: dict[AREndpoint, Callable[[str], Any]] = {
    AREndpoint.FETCH_FIRMWARE_UPDATE: read_js_variables,
    AREndpoint.FETCH_ONBOARDING: read_js_variables,
    AREndpoint.FETCH_SYSINFO: read_js_variables,
    AREndpoint.FETCH_TEMPERATURE: read_js_variables,
    AREndpoint.FETCH_PORTS_ETHERNET: read_wan_lan_status,
    AREndpoint.FETCH_UPDATE: read_netdev,
    AREndpoint.FETCH_VPN_OPENVPN_STATUS: raw_to_str,
    AREndpoint.FETCH_VPN_STATUS: read_js_variables,
}


def get_endpoint_reader(
    endpoint: AREndpoint,
) -> Callable[[str], Any]:
    """Get the content reader for the given endpoint."""

    return _ENDPOINT_READER.get(endpoint, read_json_content)
