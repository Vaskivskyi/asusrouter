"""Tests for asusrouter.modules.ports.ethernet."""

from __future__ import annotations

import pytest

from asusrouter.modules.ports.ethernet import (
    ARPortEthernetSpeed,
    read_ethernet_port_speed,
)


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        # All valid router codes
        ("t", ARPortEthernetSpeed.MBPS_10),
        ("X", ARPortEthernetSpeed.DOWN),
        ("M", ARPortEthernetSpeed.MBPS_100),
        ("G", ARPortEthernetSpeed.MBPS_1000),
        ("Q", ARPortEthernetSpeed.MBPS_2500),
        ("F", ARPortEthernetSpeed.MBPS_5000),
        ("T", ARPortEthernetSpeed.MBPS_10000),
        # Unknown codes -> UNKNOWN
        ("?", ARPortEthernetSpeed.UNKNOWN),
        ("", ARPortEthernetSpeed.UNKNOWN),
    ],
)
def test_read_ethernet_port_speed(
    code: str, expected: ARPortEthernetSpeed
) -> None:
    """Test read_ethernet_port_speed."""

    assert read_ethernet_port_speed(code) == expected
