"""Tests for asusrouter.modules.ports.base."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.ports import (
    ARPortCapability,
    ARPortSpeed,
    ARPortType,
    ARUSBSpeed,
    read_port_capabilities,
    read_port_speed,
    read_port_type,
)


def _caps(*true_caps: ARPortCapability) -> dict[ARPortCapability, bool]:
    """Build full capability dict with given caps True, rest False."""

    true_set = set(true_caps)
    return {cap: cap in true_set for cap in ARPortCapability if cap.value >= 0}


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # Non-int and negative -> early return
        (None, {}),
        ("str", {}),
        (-1, {}),
        # Zero -> all False
        (0, _caps()),
        # Single capability bits
        (1, _caps(ARPortCapability.WAN)),
        (2, _caps(ARPortCapability.LAN)),
        (128, _caps(ARPortCapability.USB)),
        (1 << 30, _caps(ARPortCapability.DUALWAN_PRIMARY)),
        # Multiple capability bits
        (3, _caps(ARPortCapability.WAN, ARPortCapability.LAN)),
        (
            (1 << 0) | (1 << 1) | (1 << 30),
            _caps(
                ARPortCapability.WAN,
                ARPortCapability.LAN,
                ARPortCapability.DUALWAN_PRIMARY,
            ),
        ),
    ],
)
def test_read_port_capabilities(
    raw: Any, expected: dict[ARPortCapability, bool]
) -> None:
    """Test read_port_capabilities."""

    assert read_port_capabilities(raw) == expected


@pytest.mark.parametrize(
    ("capabilities", "expected"),
    [
        # Empty dict -> UNKNOWN
        ({}, ARPortType.UNKNOWN),
        # Each mapped capability
        ({ARPortCapability.WAN: True}, ARPortType.WAN),
        ({ARPortCapability.LAN: True}, ARPortType.LAN),
        ({ARPortCapability.USB: True}, ARPortType.USB),
        ({ARPortCapability.MOCA: True}, ARPortType.MOCA),
        # Order: WAN checked before LAN -> WAN wins
        (
            {ARPortCapability.WAN: True, ARPortCapability.LAN: True},
            ARPortType.WAN,
        ),
        # Unmapped capability -> UNKNOWN
        ({ARPortCapability.GAME: True}, ARPortType.UNKNOWN),
        # Mapped caps all False -> UNKNOWN
        (
            {ARPortCapability.WAN: False, ARPortCapability.LAN: False},
            ARPortType.UNKNOWN,
        ),
    ],
)
def test_read_port_type(
    capabilities: dict[ARPortCapability, bool], expected: ARPortType
) -> None:
    """Test read_port_type."""

    assert read_port_type(capabilities) == expected


@pytest.mark.parametrize(
    ("port_type", "raw", "expected"),
    [
        # USB branch
        (ARPortType.USB, 5000, ARUSBSpeed.USB3),
        (ARPortType.USB, 0, ARUSBSpeed.DOWN),
        (ARPortType.USB, 999, ARUSBSpeed.UNKNOWN),
        # Ethernet branch - various non-USB port types
        (ARPortType.LAN, 1000, ARPortSpeed.MBPS_1000),
        (ARPortType.WAN, 0, ARPortSpeed.DOWN),
        (ARPortType.ETHERNET, 100, ARPortSpeed.MBPS_100),
        (ARPortType.SFPP, 10000, ARPortSpeed.MBPS_10000),
        (ARPortType.LAN, 999, ARPortSpeed.UNKNOWN),
    ],
)
def test_read_port_speed(
    port_type: ARPortType,
    raw: int,
    expected: ARPortSpeed | ARUSBSpeed,
) -> None:
    """Test read_port_speed."""

    assert read_port_speed(port_type, raw) == expected
