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
        ({}, ARUSBGeneration.UNKNOWN),
        ({ARSupportValue.USB_3.value: 1}, ARUSBGeneration.USB_3),
        ({ARSupportValue.USB_2.value: 1}, ARUSBGeneration.USB_2),
        ({ARSupportValue.USB.value: 1}, ARUSBGeneration.USB),
        # Multiple true, should return the first found
        (
            {ARSupportValue.USB_3.value: 1, ARSupportValue.USB_2.value: 1},
            ARUSBGeneration.USB_3,
        ),
        (
            {ARSupportValue.USB_2.value: 1, ARSupportValue.USB.value: 1},
            ARUSBGeneration.USB_2,
        ),
        (
            {
                ARSupportValue.USB_3.value: 0,
                ARSupportValue.USB_2.value: 0,
                ARSupportValue.USB.value: 0,
            },
            ARUSBGeneration.UNKNOWN,
        ),
        (
            {ARSupportValue.USB_3.value: "enabled"},
            ARUSBGeneration.USB_3,
        ),
        ({ARSupportValue.USB_2.value: "on"}, ARUSBGeneration.USB_2),
        ({ARSupportValue.USB.value: "1"}, ARUSBGeneration.USB),
        # Not a dict
        ("not_a_dict", ARUSBGeneration.UNKNOWN),
    ],
)
def test_translate_usb_generation(
    data: dict[str, Any], expected: ARUSBGeneration
) -> None:
    """Test translate_usb_generation returns correct generation type."""

    result = translate_usb_generation(data)
    assert result == expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({}, 0),
        ({ARSupportValue.USB_PORTS.value: 0}, 0),
        ({ARSupportValue.USB_PORTS.value: 2}, 2),
        ({ARSupportValue.USB_PORTS.value: "3"}, 3),
        ({ARSupportValue.USB_PORTS.value: "not_a_number"}, 0),
        # Not a dict
        ("not_a_dict", 0),
    ],
)
def test_translate_usb_ports(data: dict[str, Any], expected: int) -> None:
    """Test translate_usb_ports returns correct number of ports."""

    result = translate_usb_ports(data)
    assert result == expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({}, False),
        ({ARSupportValue.USB_WAN.value: 0}, False),
        ({ARSupportValue.USB_WAN.value: 1}, True),
        ({ARSupportValue.USB_WAN.value: "enabled"}, True),
        ({ARSupportValue.USB_WAN.value: "off"}, False),
        # Not a dict
        ("not_a_dict", False),
    ],
)
def test_translate_usb_wan(data: dict[str, Any], expected: bool) -> None:
    """Test translate_usb_wan returns correct WAN support."""

    result = translate_usb_wan(data)
    assert result is expected
