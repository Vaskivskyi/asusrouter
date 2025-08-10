"""Tests for the DDNS module."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from asusrouter.modules.ddns import (
    AsusDDNS,
    DDNSStatusCode,
    process_ddns,
    read_ddns_status_code,
)

ALL_KEYS = [
    "enabled",
    "hostname",
    "ip_address",
    "old_name",
    "replace_status",
    "return_code",
    "server",
    "state",
    "status",
    "status_hint",
    "updated",
]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, DDNSStatusCode.NONE),
        ("", DDNSStatusCode.NONE),
        ("Time-out", DDNSStatusCode.TIMEOUT),
        ("unknown_error", DDNSStatusCode.UNKNOWN_ERROR),
        ("connect_fail", DDNSStatusCode.CONNECT_FAIL),
        ("no_change", DDNSStatusCode.NO_CHANGE),
        ("ddns_query", DDNSStatusCode.QUERY),
        ("auth_fail", DDNSStatusCode.AUTH_FAIL),
        ("-1", DDNSStatusCode.ERROR),
        ("200", DDNSStatusCode.SUCCESS),
        ("203", DDNSStatusCode.DOMAIN_TAKEN),
        ("220", DDNSStatusCode.REGISTERED_ORIGINAL),
        ("230", DDNSStatusCode.REGISTERED_NEW),
        ("233", DDNSStatusCode.NEW_DOMAIN_TAKEN),
        ("296", DDNSStatusCode.NOT_REGISTERED),
        ("297", DDNSStatusCode.CANNOT_START_WITH_NUMBER),
        ("298", DDNSStatusCode.INVALID_DOMAIN),
        ("299", DDNSStatusCode.INVALID_IP),
        ("390", DDNSStatusCode.SERVER_ERROR),
        ("401", DDNSStatusCode.UNAUTHORIZED),
        ("402", DDNSStatusCode.FIRMWARE_UPDATE_REQUIRED),
        ("407", DDNSStatusCode.PROXY_AUTH_REQUIRED),
        ("some_unknown_code", DDNSStatusCode.OTHER),
        ("foobar", DDNSStatusCode.OTHER),
    ],
)
def test_read_ddns_status_code(
    raw: str | None,
    expected: DDNSStatusCode,
) -> None:
    """Test the read_ddns_status_code function."""

    assert read_ddns_status_code(raw) == expected


@pytest.mark.parametrize(
    ("input_data", "expected"),
    [
        # Disabled DDNS, should be INACTIVE regardless of status
        (
            {
                "ddns_enable_x": "0",
                "ddns_return_code_chk": "200",
            },
            {
                "enabled": False,
                "state": AsusDDNS.INACTIVE,
                "status": DDNSStatusCode.SUCCESS,
            },
        ),
        # Enabled, success status
        (
            {
                "ddns_enable_x": "1",
                "ddns_return_code_chk": "200",
            },
            {
                "enabled": True,
                "state": AsusDDNS.ACTIVE,
                "status": DDNSStatusCode.SUCCESS,
            },
        ),
        # Enabled, error status
        (
            {
                "ddns_enable_x": "1",
                "ddns_return_code_chk": "-1",
            },
            {
                "enabled": True,
                "state": AsusDDNS.INACTIVE,
                "status": DDNSStatusCode.ERROR,
            },
        ),
        # Enabled, unknown status
        (
            {
                "ddns_enable_x": "1",
                "ddns_return_code_chk": "foobar",
            },
            {
                "enabled": True,
                "state": AsusDDNS.INACTIVE,
                "status": DDNSStatusCode.OTHER,
            },
        ),
        # Disabled, unknown status
        (
            {
                "ddns_enable_x": "0",
                "ddns_return_code_chk": "foobar",
            },
            {
                "enabled": False,
                "state": AsusDDNS.INACTIVE,
                "status": DDNSStatusCode.OTHER,
            },
        ),
    ],
)
def test_process_ddns(
    input_data: dict[str, str],
    expected: dict[str, Any],
) -> None:
    """Test the process_ddns function."""

    result = process_ddns(input_data)
    assert result["enabled"] == expected["enabled"]
    assert result["state"] == expected["state"]
    assert result["status"] == expected["status"]


@pytest.mark.parametrize(
    ("input_data", "expected"),
    [
        (
            {
                "ddns_enable_x": "1",
                "ddns_hostname_x": "host",
                "ddns_ipaddr": "ip",
                "ddns_old_name": "old",
                "ddns_replace_status": 1,
                "ddns_return_code": "rc",
                "ddns_server_x": "server",
                "ddns_updated": "1",
                "ddns_return_code_chk": "200",
            },
            {
                "enabled": "1",
                "hostname": "host",
                "ip_address": "ip",
                "old_name": "old",
                "replace_status": 1,
                "return_code": "rc",
                "server": "server",
                "updated": "1",
            },
        ),
        (
            # Only one field present
            {"ddns_enable_x": "0"},
            {
                "enabled": "0",
                "hostname": None,
                "ip_address": None,
                "old_name": None,
                "replace_status": None,
                "return_code": None,
                "server": None,
                "updated": None,
            },
        ),
        (
            # No fields present
            {},
            {
                "enabled": None,
                "hostname": None,
                "ip_address": None,
                "old_name": None,
                "replace_status": None,
                "return_code": None,
                "server": None,
                "updated": None,
            },
        ),
    ],
)
def test_process_ddns_fields(
    input_data: dict[str, str],
    expected: dict[str, str | None],
) -> None:
    """Test that process_ddns copies or defaults all fields as expected."""

    with (
        patch("asusrouter.modules.ddns.safe_bool", side_effect=lambda x: x),
        patch("asusrouter.modules.ddns.clean_string", side_effect=lambda x: x),
    ):
        result = process_ddns(input_data)
        for key, value in expected.items():
            assert result[key] == value
        # Also check that all expected keys are present
        for key in ALL_KEYS:
            assert key in result
