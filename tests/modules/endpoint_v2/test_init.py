"""Tests for the endpoint_v2 module."""

from __future__ import annotations

import pytest

from asusrouter.const import RequestType
from asusrouter.modules.common.command import ACTION_MODE_KEY, ARActionMode
from asusrouter.modules.endpoint_v2 import (
    AREndpoint,
    AREndpointMeta,
    build_push_request,
    get_endpoint_meta,
    get_endpoint_payload_sensitivity,
    get_endpoint_raw_payload,
    get_endpoint_reader,
    get_endpoint_request_type,
)
from asusrouter.modules.endpoint_v2.translate import read_wan_lan_status
from asusrouter.tools.readers import read_js_variables, read_json_content
from asusrouter.tools.readers_v2 import read_netdev
from asusrouter.tools.security import ARSecurityLevel

GET_ENDPOINTS = (
    AREndpoint.FETCH_DIAGNOSTICS_DATA,
    AREndpoint.FETCH_NETWORK,
    AREndpoint.FETCH_PORT_STATUS,
    AREndpoint.FETCH_TRAFFIC_BACKHAUL,
    AREndpoint.FETCH_TRAFFIC_ETHERNET,
    AREndpoint.FETCH_TRAFFIC_WIFI,
)

POST_ENDPOINTS = (
    AREndpoint.FETCH_DATA,
    AREndpoint.FETCH_DEVICEMAP,
    AREndpoint.FETCH_FIRMWARE_UPDATE,
    AREndpoint.FETCH_SYSINFO,
    AREndpoint.FETCH_TEMPERATURE,
    AREndpoint.LOGIN,
    AREndpoint.LOGOUT,
    AREndpoint.PUSH_DATA,
    AREndpoint.SET_AURA,
)


def test_ar_endpoint_meta_defaults() -> None:
    """Default meta has POST request_type and DEFAULT payload sensitivity."""

    meta = AREndpointMeta()
    assert meta.request_type == RequestType.POST
    assert meta.payload_sensitivity is ARSecurityLevel.DEFAULT


def test_ar_endpoint_meta_custom_request_type() -> None:
    """Custom request_type is stored correctly."""

    meta = AREndpointMeta(request_type=RequestType.GET)
    assert meta.request_type == RequestType.GET


def test_ar_endpoint_meta_custom_sensitivity() -> None:
    """Custom payload sensitivity is stored correctly."""

    meta = AREndpointMeta(payload_sensitivity=ARSecurityLevel.UNSAFE)
    assert meta.payload_sensitivity is ARSecurityLevel.UNSAFE


@pytest.mark.parametrize("endpoint", GET_ENDPOINTS)
def test_get_endpoint_meta_get_endpoints(endpoint: AREndpoint) -> None:
    """GET endpoints return meta with request_type GET."""

    meta = get_endpoint_meta(endpoint)
    assert meta.request_type == RequestType.GET


@pytest.mark.parametrize("endpoint", POST_ENDPOINTS)
def test_get_endpoint_meta_post_endpoints(endpoint: AREndpoint) -> None:
    """Endpoints not in registry return meta with default request_type POST."""

    meta = get_endpoint_meta(endpoint)
    assert meta.request_type == RequestType.POST


def test_get_endpoint_meta_login_sensitive() -> None:
    """LOGIN endpoint payload is sensitive (UNSAFE)."""

    meta = get_endpoint_meta(AREndpoint.LOGIN)
    assert meta.payload_sensitivity is ARSecurityLevel.UNSAFE


_SENSITIVE = (AREndpoint.LOGIN, AREndpoint.WRITE_SPEEDTEST_HISTORY)
_NON_SENSITIVE = [
    e
    for e in AREndpoint
    if e not in _SENSITIVE and e is not AREndpoint.UNKNOWN
]


@pytest.mark.parametrize("endpoint", _NON_SENSITIVE)
def test_get_endpoint_meta_not_sensitive(endpoint: AREndpoint) -> None:
    """Non-sensitive endpoints keep the DEFAULT payload sensitivity."""

    meta = get_endpoint_meta(endpoint)
    assert meta.payload_sensitivity is ARSecurityLevel.DEFAULT


@pytest.mark.parametrize("endpoint", GET_ENDPOINTS)
def test_get_endpoint_request_type_get(endpoint: AREndpoint) -> None:
    """GET endpoints return RequestType.GET."""

    assert get_endpoint_request_type(endpoint) == RequestType.GET


@pytest.mark.parametrize("endpoint", POST_ENDPOINTS)
def test_get_endpoint_request_type_post(endpoint: AREndpoint) -> None:
    """Non-registered endpoints return RequestType.POST."""

    assert get_endpoint_request_type(endpoint) == RequestType.POST


@pytest.mark.parametrize("endpoint", _SENSITIVE)
def test_get_endpoint_payload_sensitivity_sensitive(
    endpoint: AREndpoint,
) -> None:
    """Sensitive endpoints require UNSAFE to log their payload."""

    assert get_endpoint_payload_sensitivity(endpoint) is ARSecurityLevel.UNSAFE


@pytest.mark.parametrize("endpoint", _NON_SENSITIVE)
def test_get_endpoint_payload_sensitivity_others(
    endpoint: AREndpoint,
) -> None:
    """Non-sensitive endpoints log their payload from DEFAULT."""

    assert (
        get_endpoint_payload_sensitivity(endpoint) is ARSecurityLevel.DEFAULT
    )


@pytest.mark.parametrize(
    "endpoint",
    [AREndpoint.RUN_SPEEDTEST, AREndpoint.SET_SPEEDTEST_START_TIME],
)
def test_get_endpoint_raw_payload_true(endpoint: AREndpoint) -> None:
    """The speedtest form endpoints send their body verbatim."""

    assert get_endpoint_raw_payload(endpoint) is True


def test_get_endpoint_raw_payload_default() -> None:
    """Other endpoints have their body quoted by default."""

    assert get_endpoint_raw_payload(AREndpoint.LOGIN) is False


_CUSTOM_READERS = {
    AREndpoint.FETCH_FIRMWARE_UPDATE: read_js_variables,
    AREndpoint.FETCH_ONBOARDING: read_js_variables,
    AREndpoint.FETCH_SYSINFO: read_js_variables,
    AREndpoint.FETCH_TEMPERATURE: read_js_variables,
    AREndpoint.FETCH_PORTS_ETHERNET: read_wan_lan_status,
    AREndpoint.FETCH_UPDATE: read_netdev,
}


@pytest.mark.parametrize(
    ("endpoint", "reader"),
    list(_CUSTOM_READERS.items()),
    ids=lambda v: v.name if isinstance(v, AREndpoint) else v.__name__,
)
def test_get_endpoint_reader_custom(
    endpoint: AREndpoint, reader: object
) -> None:
    """Endpoints with a dedicated reader resolve to it."""

    assert get_endpoint_reader(endpoint) is reader


@pytest.mark.parametrize(
    "endpoint",
    [e for e in AREndpoint if e not in _CUSTOM_READERS],
)
def test_get_endpoint_reader_default(endpoint: AREndpoint) -> None:
    """All other endpoints map to the JSON reader by default."""

    assert get_endpoint_reader(endpoint) is read_json_content


def test_build_push_request_action_mode_only() -> None:
    """A bare action mode yields a compact JSON body."""

    assert build_push_request(ARActionMode.APPLY) == '{"action_mode":"apply"}'


def test_build_push_request_default_action_mode() -> None:
    """The action mode defaults to apply."""

    assert build_push_request() == '{"action_mode":"apply"}'


def test_build_push_request_with_payload() -> None:
    """The payload is merged after the action mode, compactly encoded."""

    request = build_push_request(ARActionMode.APPLY, {"dns_ping_list": "<A>1"})
    assert request == '{"action_mode":"apply","dns_ping_list":"<A>1"}'


def test_action_mode_constants() -> None:
    """The applyapp payload keys match the device fields."""

    assert ACTION_MODE_KEY == "action_mode"
    assert ARActionMode.APPLY == "apply"
