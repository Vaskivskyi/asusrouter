"""Supported USB."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.helpers import make_enum_translator
from asusrouter.modules.usb import ARUSBCapability, ARUSBGeneration
from asusrouter.tools.converters.raw import raw_to_int
from asusrouter.tools.readers import is_true_in_dict

# First match wins
_generation = make_enum_translator(
    {
        ARSupportValue.USB_3.value: ARUSBGeneration.USB_3,
        ARSupportValue.USB_2.value: ARUSBGeneration.USB_2,
        ARSupportValue.USB.value: ARUSBGeneration.USB,
    },
    ARUSBGeneration.UNKNOWN,
)


def translate_usb_capabilities(
    data: dict[str, Any],
) -> dict[ARUSBCapability, bool | int | ARUSBGeneration]:
    """Map advertised USB capabilities; legacy devices omit the port count."""

    capabilities: dict[ARUSBCapability, bool | int | ARUSBGeneration] = {}

    generation = _generation(data)
    if generation is not ARUSBGeneration.UNKNOWN:
        capabilities[ARUSBCapability.GENERATION] = generation

    if is_true_in_dict(
        ARSupportValue.USB_MODEM.value, data
    ) and not is_true_in_dict(ARSupportValue.USB_NO_MODEM.value, data):
        capabilities[ARUSBCapability.MODEM] = True

    ports = raw_to_int(data.get(ARSupportValue.USB_PORTS.value))
    if ports:
        capabilities[ARUSBCapability.PORTS_COUNT] = ports

    if is_true_in_dict(ARSupportValue.USB_WAN.value, data):
        capabilities[ARUSBCapability.WAN] = True
    return capabilities


def translate_usb(data: dict[str, Any]) -> bool:
    """Report whether the device advertises any USB capability."""

    return bool(translate_usb_capabilities(data))
