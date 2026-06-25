"""Tests for the endpoint_v2 module."""

from __future__ import annotations

import pytest

from asusrouter.const import RequestType
from asusrouter.modules.endpoint_v2 import (
    AREndpoint,
    AREndpointMeta,
    get_endpoint_meta,
    get_endpoint_reader,
    get_endpoint_request_type,
    get_endpoint_sensitive,
)
from asusrouter.modules.endpoint_v2.translate import read_wan_lan_status
from asusrouter.tools.readers import read_js_variables, read_json_content

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
    """Default meta has POST request_type and sensitive=False."""

    meta = AREndpointMeta()
    assert meta.request_type == RequestType.POST
    assert meta.sensitive is False


def test_ar_endpoint_meta_custom_request_type() -> None:
    """Custom request_type is stored correctly."""

    meta = AREndpointMeta(request_type=RequestType.GET)
    assert meta.request_type == RequestType.GET


def test_ar_endpoint_meta_custom_sensitive() -> None:
    """Custom sensitive flag is stored correctly."""

    meta = AREndpointMeta(sensitive=True)
    assert meta.sensitive is True


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
    """LOGIN endpoint is marked as sensitive."""

    meta = get_endpoint_meta(AREndpoint.LOGIN)
    assert meta.sensitive is True


_NON_SENSITIVE = [
    e
    for e in AREndpoint
    if e is not AREndpoint.LOGIN and e is not AREndpoint.UNKNOWN
]


@pytest.mark.parametrize("endpoint", _NON_SENSITIVE)
def test_get_endpoint_meta_not_sensitive(endpoint: AREndpoint) -> None:
    """Non-login endpoints are not sensitive."""

    meta = get_endpoint_meta(endpoint)
    assert meta.sensitive is False


@pytest.mark.parametrize("endpoint", GET_ENDPOINTS)
def test_get_endpoint_request_type_get(endpoint: AREndpoint) -> None:
    """GET endpoints return RequestType.GET."""

    assert get_endpoint_request_type(endpoint) == RequestType.GET


@pytest.mark.parametrize("endpoint", POST_ENDPOINTS)
def test_get_endpoint_request_type_post(endpoint: AREndpoint) -> None:
    """Non-registered endpoints return RequestType.POST."""

    assert get_endpoint_request_type(endpoint) == RequestType.POST


def test_get_endpoint_sensitive_login() -> None:
    """LOGIN endpoint is sensitive."""

    assert get_endpoint_sensitive(AREndpoint.LOGIN) is True


@pytest.mark.parametrize("endpoint", _NON_SENSITIVE)
def test_get_endpoint_sensitive_others(endpoint: AREndpoint) -> None:
    """Non-login endpoints are not sensitive."""

    assert get_endpoint_sensitive(endpoint) is False


_CUSTOM_READERS = {
    AREndpoint.FETCH_ONBOARDING: read_js_variables,
    AREndpoint.FETCH_TEMPERATURE: read_js_variables,
    AREndpoint.FETCH_PORTS_ETHERNET: read_wan_lan_status,
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
