"""Supported USB."""

from __future__ import annotations

from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.helpers import (
    make_bool_translator,
    make_enum_translator,
    make_int_translator,
)
from asusrouter.modules.usb import ARUSBGeneration

# First match wins
translate_usb_generation = make_enum_translator(
    {
        ARSupportValue.USB_3.value: ARUSBGeneration.USB_3,
        ARSupportValue.USB_2.value: ARUSBGeneration.USB_2,
        ARSupportValue.USB.value: ARUSBGeneration.USB,
    },
    ARUSBGeneration.UNKNOWN,
)

translate_usb_ports = make_int_translator(ARSupportValue.USB_PORTS.value)

translate_usb_wan = make_bool_translator(ARSupportValue.USB_WAN.value)
