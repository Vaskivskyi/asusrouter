"""Supported USB."""

from __future__ import annotations

from enum import IntEnum
from typing import Any

from asusrouter.const import UNKNOWN_MEMBER
from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.tools.converters import safe_bool_nn, safe_int_nn
from asusrouter.tools.enum import FromIntMixin
from asusrouter.tools.readers import is_true_in_dict


class ARSupportUSBGeneration(FromIntMixin, IntEnum):
    """USB generation types."""

    UNKNOWN = UNKNOWN_MEMBER

    USB = 1
    USB_2 = 2
    USB_3 = 3


def translate_usb_generation(data: dict[str, Any]) -> ARSupportUSBGeneration:
    """Translate USB generation data to ARSupportUSBGeneration."""

    if not isinstance(data, dict):
        return ARSupportUSBGeneration.UNKNOWN  # type: ignore[unreachable]

    if is_true_in_dict(ARSupportValue.USB_3.value, data):
        return ARSupportUSBGeneration.USB_3

    if is_true_in_dict(ARSupportValue.USB_2.value, data):
        return ARSupportUSBGeneration.USB_2

    if is_true_in_dict(ARSupportValue.USB.value, data):
        return ARSupportUSBGeneration.USB

    return ARSupportUSBGeneration.UNKNOWN


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
