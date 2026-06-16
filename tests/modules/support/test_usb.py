"""Tests for the support usb module."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.usb import (
    translate_usb_generation,
    translate_usb_ports,
    translate_usb_wan,
)
from asusrouter.modules.usb import ARUSBGeneration


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({ARSupportValue.USB_3.value: 1}, ARUSBGeneration.USB_3),
        ({ARSupportValue.USB_2.value: 1}, ARUSBGeneration.USB_2),
        ({ARSupportValue.USB.value: 1}, ARUSBGeneration.USB),
        # USB_3 takes priority
        (
            {ARSupportValue.USB_3.value: 1, ARSupportValue.USB_2.value: 1},
            ARUSBGeneration.USB_3,
        ),
        ({}, ARUSBGeneration.UNKNOWN),
    ],
)
def test_translate_usb_generation(
    data: dict[str, Any], expected: ARUSBGeneration
) -> None:
    """Test translate_usb_generation returns correct generation type."""

    assert translate_usb_generation(data) == expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({ARSupportValue.USB_PORTS.value: 2}, 2),
        ({ARSupportValue.USB_PORTS.value: "0"}, 0),
        ({}, 0),
    ],
)
def test_translate_usb_ports(data: dict[str, Any], expected: int) -> None:
    """Test translate_usb_ports returns correct number of ports."""

    result = translate_usb_ports(data)
    assert result == expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({ARSupportValue.USB_WAN.value: 1}, True),
        ({ARSupportValue.USB_WAN.value: "0"}, False),
        ({}, False),
    ],
)
def test_translate_usb_wan(data: dict[str, Any], expected: bool) -> None:
    """Test translate_usb_wan returns correct WAN support."""

    result = translate_usb_wan(data)
    assert result is expected
