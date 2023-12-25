"""Tests for the access point module."""

from __future__ import annotations

import pytest

from asusrouter.modules.access_point import AccessPoint


@pytest.mark.parametrize(
    "mac, ssid, hidden, mac_fh, ssid_fh",
    [
        ("mac", "ssid", True, "mac_fh", "ssid_fh"),
        ("mac", "ssid", False, "mac_fh", "ssid_fh"),
        ("mac", "ssid", True, None, None),
        ("mac", "ssid", False, None, None),
        (None, None, None, None, None),
    ],
)
def test_access_point(mac, ssid, hidden, mac_fh, ssid_fh):
    """Test the access point class."""

    # Create the access point
    access_point = AccessPoint(
        mac=mac,
        ssid=ssid,
        hidden=hidden,
        mac_fh=mac_fh,
        ssid_fh=ssid_fh,
    )

    # Check the access point
    assert access_point.mac == mac
    assert access_point.ssid == ssid
    assert access_point.hidden == hidden
    assert access_point.mac_fh == mac_fh
    assert access_point.ssid_fh == ssid_fh
