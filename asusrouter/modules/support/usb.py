"""Supported USB."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.usb import ARUSBGeneration
from asusrouter.tools.converters import safe_bool_nn, safe_int_nn
from asusrouter.tools.readers import is_true_in_dict


def translate_usb_generation(data: dict[str, Any]) -> ARUSBGeneration:
    """Translate USB generation data to ARUSBGeneration."""

    if not isinstance(data, dict):
        return ARUSBGeneration.UNKNOWN  # type: ignore[unreachable]

    if is_true_in_dict(ARSupportValue.USB_3.value, data):
        return ARUSBGeneration.USB_3

    if is_true_in_dict(ARSupportValue.USB_2.value, data):
        return ARUSBGeneration.USB_2

    if is_true_in_dict(ARSupportValue.USB.value, data):
        return ARUSBGeneration.USB

    return ARUSBGeneration.UNKNOWN


def translate_usb_ports(data: dict[str, Any]) -> int:
    """Translate USB ports data to number of ports."""

    if isinstance(data, dict):
        return safe_int_nn(data.get(ARSupportValue.USB_PORTS.value))

    return 0  # type: ignore[unreachable]


def translate_usb_wan(data: dict[str, Any]) -> bool:
    """Translate USB WAN support data to boolean."""

    if isinstance(data, dict):
        return safe_bool_nn(data.get(ARSupportValue.USB_WAN.value))

    return False  # type: ignore[unreachable]
