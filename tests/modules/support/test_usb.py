"""Tests for the support usb module."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.usb import (
    translate_usb,
    translate_usb_capabilities,
)
from asusrouter.modules.usb import ARUSBCapability, ARUSBGeneration


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({ARSupportValue.USB.value: 1}, True),
        ({ARSupportValue.USB_MODEM.value: 1}, True),
        ({}, False),
    ],
)
def test_translate_usb(data: Any, expected: bool) -> None:
    """Test translate_usb reports any USB capability."""

    assert translate_usb(data) is expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({}, {}),
        # Generation, highest wins
        (
            {ARSupportValue.USB_3.value: 1, ARSupportValue.USB_2.value: 1},
            {ARUSBCapability.GENERATION: ARUSBGeneration.USB_3},
        ),
        # Legacy: USB present but no port count reported
        (
            {ARSupportValue.USB_2.value: 1},
            {ARUSBCapability.GENERATION: ARUSBGeneration.USB_2},
        ),
        # Port count included only when reported
        (
            {
                ARSupportValue.USB.value: 1,
                ARSupportValue.USB_PORTS.value: 2,
            },
            {
                ARUSBCapability.GENERATION: ARUSBGeneration.USB,
                ARUSBCapability.PORTS_COUNT: 2,
            },
        ),
        # Modem and WAN as bool capabilities
        (
            {
                ARSupportValue.USB_3.value: 1,
                ARSupportValue.USB_MODEM.value: 1,
                ARSupportValue.USB_WAN.value: 1,
            },
            {
                ARUSBCapability.GENERATION: ARUSBGeneration.USB_3,
                ARUSBCapability.MODEM: True,
                ARUSBCapability.WAN: True,
            },
        ),
        # nomodem disables the modem capability even when modem is set
        (
            {
                ARSupportValue.USB.value: 1,
                ARSupportValue.USB_MODEM.value: 1,
                ARSupportValue.USB_NO_MODEM.value: 1,
            },
            {ARUSBCapability.GENERATION: ARUSBGeneration.USB},
        ),
        # A zero port count is dropped
        (
            {
                ARSupportValue.USB.value: 1,
                ARSupportValue.USB_PORTS.value: "0",
            },
            {ARUSBCapability.GENERATION: ARUSBGeneration.USB},
        ),
    ],
)
def test_translate_usb_capabilities(
    data: Any, expected: dict[ARUSBCapability, bool | int | ARUSBGeneration]
) -> None:
    """Test translate_usb_capabilities maps USB capabilities."""

    assert translate_usb_capabilities(data) == expected
