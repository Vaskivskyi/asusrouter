"""Endpoint V2 module for AsusRouter."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR, RequestType
from asusrouter.tools.enum import FromStrMixin


class AREndpoint(FromStrMixin, StrEnum):
    """Endpoint enum.

    Values are the URL paths used to communicate with the device.
    """

    UNKNOWN = UNKNOWN_MEMBER_STR

    # Read endpoints
    FETCH_CLIENTS_UPDATE = "update_clients.asp"
    FETCH_DATA = "appGet.cgi"
    FETCH_DEVICEMAP = "ajax_status.xml"
    FETCH_FIRMWARE_UPDATE = "detect_firmware.asp"
    FETCH_FIRMWARE_UPDATE_NOTE = "release_note0.asp"
    FETCH_FIRMWARE_UPDATE_NOTE_AIMESH = "release_note_amas.asp"
    FETCH_NETWORK = "netool.cgi"
    FETCH_ONBOARDING = "ajax_onboarding.asp"
    FETCH_PORT_STATUS = "get_port_status.cgi"
    FETCH_PORTS_ETHERNET = "ajax_ethernet_ports.asp"
    FETCH_SYSINFO = "ajax_sysinfo.asp"
    FETCH_TEMPERATURE = "ajax_coretmp.asp"
    FETCH_TRAFFIC_BACKHAUL = "get_diag_sta_traffic.cgi"
    FETCH_TRAFFIC_ETHERNET = "get_diag_eth_traffic.cgi"
    FETCH_TRAFFIC_WIFI = "get_diag_wifi_traffic.cgi"
    FETCH_VPN_STATUS = "ajax_vpn_status.asp"

    # Write endpoints
    PUSH_DATA = "applyapp.cgi"
    SET_AURA = "set_ledg.cgi"

    # Service endpoints
    LOGIN = "login.cgi"
    LOGOUT = "Logout.asp"


# Endpoints pending V2 migration (used in V1)
#     # Control endpoints
#     APPLY = "apply.cgi"

# Endpoints defined in V1 but never used
#     CERT_INFO = "ajax_certinfo.asp"
#     DDNS_CODE = "ajax_ddnscode.asp"
#     DSL = "ajax_AdslStatus.asp"
#     NETWORKMAPD = "update_networkmapd.asp"
#     STATE = "state.js"


@dataclass
class AREndpointMeta:
    """Metadata for an AREndpoint."""

    request_type: RequestType = RequestType.POST
    sensitive: bool = False


_GET_META = AREndpointMeta(request_type=RequestType.GET)

_ENDPOINT_META: dict[AREndpoint, AREndpointMeta] = {
    AREndpoint.FETCH_NETWORK: _GET_META,
    AREndpoint.FETCH_PORT_STATUS: _GET_META,
    AREndpoint.FETCH_TRAFFIC_BACKHAUL: _GET_META,
    AREndpoint.FETCH_TRAFFIC_ETHERNET: _GET_META,
    AREndpoint.FETCH_TRAFFIC_WIFI: _GET_META,
    AREndpoint.LOGIN: AREndpointMeta(sensitive=True),
}


def get_endpoint_meta(endpoint: AREndpoint) -> AREndpointMeta:
    """Get metadata for the given endpoint."""

    return _ENDPOINT_META.get(endpoint, AREndpointMeta())


def get_endpoint_request_type(endpoint: AREndpoint) -> RequestType:
    """Get the request type for the given endpoint."""

    return get_endpoint_meta(endpoint).request_type


def get_endpoint_sensitive(endpoint: AREndpoint) -> bool:
    """Check if the given endpoint is sensitive."""

    return get_endpoint_meta(endpoint).sensitive
