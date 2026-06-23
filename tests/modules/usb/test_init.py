"""Tests for asusrouter.modules.usb."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.usb import ARUSBDevice, ARUSBDeviceType, ARUSBSpeed

_STORAGE_RAW = {
    "type": "storage",
    "manu": "JetFlash",
    "product": "Mass Storage Device",
    "serial": "08MAGWFG85JV4MQ1",
    "speed": "5000",
    "dev_name": "JetFlash Transcend 64GB",
    "size_kb": "59038688",
    "used_kb": "6226272",
}
_MODEM_RAW = {
    "type": "modem",
    "manu": "SAMSUNG",
    "product": "SAMSUNG_Android",
    "serial": "RFGL116XG1B",
    "speed": "5000",
}
_SENTINEL_RAW = {
    "type": "storage",
    "manu": "-1",
    "product": "-1",
    "serial": "-1",
    "speed": "0",
    "dev_name": "TS-RDF5 SD Transcend",
    "size_kb": "125026304",
    "used_kb": "0",
}


class TestARUSBSpeed:
    """Tests for ARUSBSpeed."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (0, ARUSBSpeed.DOWN),
            (480, ARUSBSpeed.USB2),
            (5000, ARUSBSpeed.USB3),
            (10000, ARUSBSpeed.USB3_1),
            (20000, ARUSBSpeed.USB3_2),
            (999, ARUSBSpeed.UNKNOWN),
            (-1, ARUSBSpeed.UNKNOWN),
        ],
    )
    def test_from_value(self, value: int, expected: ARUSBSpeed) -> None:
        """ARUSBSpeed.from_value maps Mbps to the speed grade."""

        assert ARUSBSpeed.from_value(value) == expected


class TestARUSBDeviceType:
    """Tests for ARUSBDeviceType."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("storage", ARUSBDeviceType.STORAGE),
            ("modem", ARUSBDeviceType.MODEM),
            ("other", ARUSBDeviceType.UNKNOWN),
            (None, ARUSBDeviceType.UNKNOWN),
        ],
    )
    def test_from_value(self, value: Any, expected: ARUSBDeviceType) -> None:
        """ARUSBDeviceType.from_value maps the raw type string."""

        assert ARUSBDeviceType.from_value(value) == expected


class TestARUSBDeviceFromRaw:
    """Tests for ARUSBDevice.from_raw."""

    def test_storage_device(self) -> None:
        """A storage device parses all fields, size in bytes."""

        device = ARUSBDevice.from_raw("2", _STORAGE_RAW)

        assert device.serial == "08MAGWFG85JV4MQ1"
        assert device.manufacturer_raw == "JetFlash"
        assert device.type == ARUSBDeviceType.STORAGE
        assert device.name == "JetFlash Transcend 64GB"
        assert device.speed == ARUSBSpeed.USB3
        assert device.position == "2"
        assert device.size == 59038688 * 1024
        assert device.used == 6226272 * 1024

    def test_modem_device(self) -> None:
        """A modem has no storage fields."""

        device = ARUSBDevice.from_raw("1", _MODEM_RAW)

        assert device.type == ARUSBDeviceType.MODEM
        assert device.name is None
        assert device.size is None
        assert device.used is None

    def test_sentinel_fields_become_none(self) -> None:
        """The `-1` sentinel maps string fields to None."""

        device = ARUSBDevice.from_raw("1.1", _SENTINEL_RAW)

        assert device.serial is None
        assert device.manufacturer_raw is None
        assert device.product is None
        assert device.speed == ARUSBSpeed.DOWN
        assert device.name == "TS-RDF5 SD Transcend"


class TestARUSBDeviceIdentity:
    """Tests for ARUSBDevice equality and hashing."""

    def test_equal_by_serial_and_manufacturer(self) -> None:
        """Same serial+manufacturer match despite transient fields."""

        a = ARUSBDevice(serial="X", manufacturer_raw="Y", used=1, position="1")
        b = ARUSBDevice(
            serial="X", manufacturer_raw="Y", used=999, position="2.3"
        )

        assert a == b
        assert hash(a) == hash(b)

    def test_not_equal_on_different_serial(self) -> None:
        """Different serials are different devices."""

        a = ARUSBDevice(serial="X", manufacturer_raw="Y")
        b = ARUSBDevice(serial="Z", manufacturer_raw="Y")

        assert a != b

    def test_hashable_for_grouping(self) -> None:
        """Devices group by identity in a set."""

        a = ARUSBDevice(serial="X", manufacturer_raw="Y", used=1)
        b = ARUSBDevice(serial="X", manufacturer_raw="Y", used=2)
        c = ARUSBDevice(serial="Z", manufacturer_raw="Y")

        assert len({a, b, c}) == 2
