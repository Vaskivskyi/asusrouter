"""USB module for AsusRouter."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from typing import Any

from asusrouter.const import UNKNOWN_MEMBER, UNKNOWN_MEMBER_STR
from asusrouter.tools.converters.raw import raw_to_int, raw_to_str
from asusrouter.tools.enum import FromIntMixin, FromStrMixin
from asusrouter.tools.units import DataUnitConverter, UnitOfData

# Asus reports sizes in KiB despite labelling them `_kb`
_kib_to_byte = DataUnitConverter.converter_factory(
    UnitOfData.KIBIBYTE, UnitOfData.BYTE
)
# Sentinel the device uses for unavailable string fields
_UNAVAILABLE = "-1"


class ARUSBCapability(FromStrMixin, StrEnum):
    """USB capabilities a device advertises. Acts as a database."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    GENERATION = "generation"
    MODEM = "modem"
    PORTS_COUNT = "ports_count"
    WAN = "wan"


class ARUSBGeneration(FromIntMixin, IntEnum):
    """USB generation types."""

    UNKNOWN = UNKNOWN_MEMBER

    USB = 1
    USB_2 = 2
    USB_3 = 3


class ARUSBSpeed(FromIntMixin, IntEnum):
    """USB link speed in Mbps."""

    UNKNOWN = UNKNOWN_MEMBER

    DOWN = 0
    USB2 = 480
    USB3 = 5000
    USB3_1 = 10000
    USB3_2 = 20000


class ARUSBDeviceType(FromStrMixin, StrEnum):
    """Type of a connected USB device."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    MODEM = "modem"
    STORAGE = "storage"


def _clean_str(value: Any) -> str | None:
    """Read a string field, mapping the `-1` sentinel to None."""

    text = raw_to_str(value)
    if text is None or text == _UNAVAILABLE:
        return None
    return text


def _kib_to_bytes(value: Any) -> int | None:
    """Convert a KiB value to bytes, or None when unavailable."""

    kib = raw_to_int(value)
    if kib is None:
        return None
    return int(_kib_to_byte(kib))


@dataclass(frozen=True)
class ARUSBDevice:
    """A device connected to a USB port.

    Identity is the raw serial and manufacturer; everything else
    (location, capacity, negotiated speed, usage) is descriptive and
    excluded from equality so the same device matches across fetches
    and reconnects.
    """

    # Identity
    serial: str | None = None
    manufacturer_raw: str | None = None

    # Descriptive — not part of identity
    type: ARUSBDeviceType = field(
        default=ARUSBDeviceType.UNKNOWN, compare=False
    )
    product: str | None = field(default=None, compare=False)
    name: str | None = field(default=None, compare=False)
    speed: ARUSBSpeed = field(default=ARUSBSpeed.UNKNOWN, compare=False)
    position: str | None = field(default=None, compare=False)
    size: int | None = field(default=None, compare=False)
    used: int | None = field(default=None, compare=False)

    @classmethod
    def from_raw(cls, position: str, raw: dict[str, Any]) -> ARUSBDevice:
        """Build a device from a raw `devices` entry."""

        return cls(
            serial=_clean_str(raw.get("serial")),
            manufacturer_raw=_clean_str(raw.get("manu")),
            type=ARUSBDeviceType.from_value(raw.get("type")),
            product=_clean_str(raw.get("product")),
            name=_clean_str(raw.get("dev_name")),
            speed=ARUSBSpeed.from_value(raw_to_int(raw.get("speed")) or 0),
            position=position,
            size=_kib_to_bytes(raw.get("size_kb")),
            used=_kib_to_bytes(raw.get("used_kb")),
        )
