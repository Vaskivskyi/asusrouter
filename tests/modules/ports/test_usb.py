"""Tests for asusrouter.modules.ports.usb."""

from __future__ import annotations

import pytest

from asusrouter.modules.ports.usb import ARPortUSBSpeed


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, ARPortUSBSpeed.DOWN),
        (480, ARPortUSBSpeed.USB2),
        (5000, ARPortUSBSpeed.USB3),
        (10000, ARPortUSBSpeed.USB3_1),
        (20000, ARPortUSBSpeed.USB3_2),
        # Unknown values -> UNKNOWN
        (999, ARPortUSBSpeed.UNKNOWN),
        (-1, ARPortUSBSpeed.UNKNOWN),
    ],
)
def test_arportusb_speed_from_value(
    value: int, expected: ARPortUSBSpeed
) -> None:
    """Test ARPortUSBSpeed.from_value."""

    assert ARPortUSBSpeed.from_value(value) == expected
