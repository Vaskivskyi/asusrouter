"""Tests for the device identity module."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from asusrouter.const import DEFAULT_IDENTITY_BRAND
from asusrouter.modules.aimesh.topology import ARAiMeshTopology
from asusrouter.modules.device.identity import (
    ARDeviceIdentity,
    _translate_firmware,
    _translate_identity_base,
    _translate_wifi,
)
from asusrouter.modules.firmware import ARFirmware
from asusrouter.modules.nvram import ARNvramType
from asusrouter.modules.support import ARSupportSourceUniversal
from asusrouter.modules.support.flag import ARSupportType
from asusrouter.modules.wifi import ARWiFiBand


class TestTranslateFirmware:
    """Tests for _translate_firmware."""

    @pytest.mark.parametrize(
        ("data", "expected_major", "expected_minor", "expected_build"),
        [
            (
                {
                    ARNvramType.FW_MAJOR: "3.0.0.4",
                    ARNvramType.FW_MINOR: 388,
                    ARNvramType.FW_BUILD: "40456_g8178ee0",
                },
                (3, 0, 0, 4),
                388,
                40456,
            ),
            (
                {
                    ARNvramType.FW_MAJOR: "9.0.0.6",
                    ARNvramType.FW_MINOR: "102",
                    ARNvramType.FW_BUILD: "4856_g8178ee0",
                },
                (9, 0, 0, 6),
                102,
                4856,
            ),
            ({}, None, None, None),
        ],
    )
    def test_translate_firmware(
        self,
        data: dict[Any, Any],
        expected_major: tuple[int, ...] | None,
        expected_minor: int | None,
        expected_build: int | None,
    ) -> None:
        """Reads FW_MAJOR/MINOR/BUILD keys and builds ARFirmware."""

        fw = _translate_firmware(data)
        assert isinstance(fw, ARFirmware)
        assert fw.major == expected_major
        assert fw.minor == expected_minor
        assert fw.build == expected_build


class TestTranslateWifi:
    """Tests for _translate_wifi."""

    @pytest.mark.parametrize(
        ("data", "support", "expected"),
        [
            (
                {ARNvramType.WIRELESS_BANDS: "2g1&#605g1"},
                {ARSupportType.WIFI_UNITS: (0, 1)},
                {ARWiFiBand.BAND_2G1: 0, ARWiFiBand.BAND_5G1: 1},
            ),
            (
                {ARNvramType.WIRELESS_BANDS: "2g1&#605g1&#605g2"},
                {ARSupportType.WIFI_UNITS: (0, 1, 2)},
                {
                    ARWiFiBand.BAND_2G1: 0,
                    ARWiFiBand.BAND_5G1: 1,
                    ARWiFiBand.BAND_5G2: 2,
                },
            ),
            # Invalid band string raises ValueError in ARWiFiBand → skipped
            (
                {ARNvramType.WIRELESS_BANDS: "2g1&#60invalid_band&#605g1"},
                {ARSupportType.WIFI_UNITS: (0, 1, 2)},
                {ARWiFiBand.BAND_2G1: 0, ARWiFiBand.BAND_5G1: 2},
            ),
            # No WIFI_UNITS → zip stops immediately
            (
                {ARNvramType.WIRELESS_BANDS: "2g1&#605g1"},
                {},
                {},
            ),
            # Empty band string
            (
                {ARNvramType.WIRELESS_BANDS: ""},
                {ARSupportType.WIFI_UNITS: (0, 1)},
                {},
            ),
            # Missing WIRELESS_BANDS key
            (
                {},
                {ARSupportType.WIFI_UNITS: (0, 1)},
                {},
            ),
            # Fewer ids than bands → zip stops early
            (
                {ARNvramType.WIRELESS_BANDS: "2g1&#605g1&#605g2"},
                {ARSupportType.WIFI_UNITS: (0,)},
                {ARWiFiBand.BAND_2G1: 0},
            ),
            # ARWiFiBand.UNKNOWN is a valid member ("unknown")
            # but must be skipped
            (
                {ARNvramType.WIRELESS_BANDS: "2g1&#60unknown&#605g1"},
                {ARSupportType.WIFI_UNITS: (0, 1, 2)},
                {ARWiFiBand.BAND_2G1: 0, ARWiFiBand.BAND_5G1: 2},
            ),
        ],
    )
    def test_translate_wifi(
        self,
        data: dict[Any, Any],
        support: dict[ARSupportType, Any],
        expected: dict[ARWiFiBand, int],
    ) -> None:
        """Parses bands string and WIFI_UNITS into ARWiFiBand dict."""

        assert _translate_wifi(data, support) == expected


class TestTranslateIdentityBase:
    """Tests for _translate_identity_base."""

    @pytest.mark.parametrize(
        (
            "data",
            "expected_mac_asus",
            "expected_model",
            "expected_original",
            "expected_serial",
        ),
        [
            (
                {
                    ARNvramType.MAC: "AA:BB:CC:11:22:33",
                    ARNvramType.MODEL: "RT-AX88U",
                    ARNvramType.MODEL_ORIGINAL: "RT-AX88U_V2",
                    ARNvramType.SERIAL: "ABC123XYZ",
                },
                "AA:BB:CC:11:22:33",
                "RT-AX88U",
                "RT-AX88U_V2",
                "ABC123XYZ",
            ),
            # Lowercase MAC is parsed and can round-trip as_asus()
            (
                {
                    ARNvramType.MAC: "aa:bb:cc:11:22:33",
                    ARNvramType.MODEL: "RT-AX56U",
                    ARNvramType.MODEL_ORIGINAL: None,
                    ARNvramType.SERIAL: None,
                },
                "AA:BB:CC:11:22:33",
                "RT-AX56U",
                None,
                None,
            ),
            # All missing → all None
            ({}, None, None, None, None),
        ],
    )
    def test_translate_identity_base(
        self,
        data: dict[Any, Any],
        expected_mac_asus: str | None,
        expected_model: str | None,
        expected_original: str | None,
        expected_serial: str | None,
    ) -> None:
        """Extracts MAC, model, model_original, serial from data."""

        mac, model, model_original, serial = _translate_identity_base(data)
        if expected_mac_asus is None:
            assert mac is None
        else:
            assert mac is not None
            assert mac.as_asus() == expected_mac_asus
        assert model == expected_model
        assert model_original == expected_original
        assert serial == expected_serial


class TestARDeviceIdentityInit:
    """Tests for ARDeviceIdentity.__init__ defaults."""

    def test_defaults(self) -> None:
        """Fresh instance has expected default values for all attributes."""

        identity = ARDeviceIdentity()
        assert identity.brand == DEFAULT_IDENTITY_BRAND
        assert isinstance(identity.firmware, ARFirmware)
        assert identity.firmware == ARFirmware()
        assert identity.mac is None
        assert identity.model is None
        assert identity.model_original is None
        assert identity.serial is None
        assert identity.support == {}
        assert identity.wifi == {}


class TestARDeviceIdentityProperties:
    """Tests for ARDeviceIdentity property accessors."""

    def test_brand(self) -> None:
        """Brand returns the internal _brand value."""

        identity = ARDeviceIdentity()
        assert identity.brand == DEFAULT_IDENTITY_BRAND

    def test_firmware(self) -> None:
        """Firmware returns the internal _firmware value."""

        identity = ARDeviceIdentity()
        fw = ARFirmware((3, 0, 0, 4), 388, 8)
        identity._firmware = fw
        assert identity.firmware is fw

    def test_mac(self) -> None:
        """Mac returns None by default and the set value after assignment."""

        identity = ARDeviceIdentity()
        assert identity.mac is None

    def test_model(self) -> None:
        """Model returns None by default."""

        identity = ARDeviceIdentity()
        assert identity.model is None

    def test_model_original(self) -> None:
        """model_original returns None by default."""

        identity = ARDeviceIdentity()
        assert identity.model_original is None

    def test_serial(self) -> None:
        """Serial returns None by default."""

        identity = ARDeviceIdentity()
        assert identity.serial is None

    def test_support(self) -> None:
        """Support returns empty dict by default."""

        identity = ARDeviceIdentity()
        assert identity.support == {}

    def test_wifi(self) -> None:
        """Wifi returns empty dict by default."""

        identity = ARDeviceIdentity()
        assert identity.wifi == {}


class TestARDeviceIdentityBuild:
    """Tests for ARDeviceIdentity.build classmethod."""

    def test_build_full_data(self) -> None:
        """Build populates all fields from a complete data dict."""

        support_data = {ARSupportType.WIFI_UNITS: (0, 1)}
        data: dict[Any, Any] = {
            ARSupportSourceUniversal: support_data,
            ARNvramType.FW_MAJOR: "3.0.0.4",
            ARNvramType.FW_MINOR: 388,
            ARNvramType.FW_BUILD: "40456_g8178ee0",
            ARNvramType.MAC: "AA:BB:CC:11:22:33",
            ARNvramType.MODEL: "RT-AX88U",
            ARNvramType.MODEL_ORIGINAL: "RT-AX88U_V2",
            ARNvramType.SERIAL: "ABC123XYZ",
            ARNvramType.WIRELESS_BANDS: "2g1&#605g1",
        }
        identity = ARDeviceIdentity.build(data)

        assert isinstance(identity, ARDeviceIdentity)
        assert identity.support is support_data
        assert identity.firmware.major == (3, 0, 0, 4)
        assert identity.firmware.minor == 388
        assert identity.firmware.build == 40456
        assert identity.mac is not None
        assert identity.mac.as_asus() == "AA:BB:CC:11:22:33"
        assert identity.model == "RT-AX88U"
        assert identity.model_original == "RT-AX88U_V2"
        assert identity.serial == "ABC123XYZ"
        assert identity.wifi == {
            ARWiFiBand.BAND_2G1: 0,
            ARWiFiBand.BAND_5G1: 1,
        }

    def test_build_support_not_dict_falls_back_to_empty(self) -> None:
        """Build treats non-dict support value as empty dict."""

        data: dict[Any, Any] = {ARSupportSourceUniversal: "not_a_dict"}
        identity = ARDeviceIdentity.build(data)
        assert identity.support == {}

    def test_build_support_none_falls_back_to_empty(self) -> None:
        """Build treats None support value as empty dict."""

        data: dict[Any, Any] = {ARSupportSourceUniversal: None}
        identity = ARDeviceIdentity.build(data)
        assert identity.support == {}

    def test_build_empty_data(self) -> None:
        """Build with empty data produces all-default identity."""

        identity = ARDeviceIdentity.build({})
        assert identity.support == {}
        assert identity.firmware == ARFirmware()
        assert identity.mac is None
        assert identity.model is None
        assert identity.model_original is None
        assert identity.serial is None
        assert identity.wifi == {}


class TestAimesh:
    """Tests for the live AiMesh topology on the identity."""

    def test_default_is_empty_topology(self) -> None:
        """A fresh identity carries an empty topology."""

        aimesh = ARDeviceIdentity().aimesh

        assert isinstance(aimesh, ARAiMeshTopology)
        assert aimesh.nodes == {}

    def test_update_swaps_snapshot(self) -> None:
        """update_aimesh replaces the whole snapshot."""

        identity = ARDeviceIdentity()
        topology = ARAiMeshTopology()

        identity.update_aimesh(topology)

        assert identity.aimesh is topology


class TestBoottime:
    """Tests for the live boot time on the identity."""

    def test_default_is_none(self) -> None:
        """A fresh identity carries no boot time."""

        assert ARDeviceIdentity().boottime is None

    def test_update_sets_boottime(self) -> None:
        """update_boottime stores the value."""

        identity = ARDeviceIdentity()
        boottime = datetime(2026, 1, 1, tzinfo=UTC)

        identity.update_boottime(boottime)

        assert identity.boottime == boottime

    def test_first_boottime_is_not_a_reboot(self) -> None:
        """Setting boot time from None does not flag a reboot."""

        identity = ARDeviceIdentity()

        identity.update_boottime(datetime(2026, 1, 1, tzinfo=UTC))

        assert identity.rebooted is False

    def test_unchanged_boottime_is_not_a_reboot(self) -> None:
        """Re-setting the same boot time does not flag a reboot."""

        identity = ARDeviceIdentity()
        boottime = datetime(2026, 1, 1, tzinfo=UTC)
        identity.update_boottime(boottime)

        identity.update_boottime(boottime)

        assert identity.rebooted is False

    def test_moved_boottime_flags_reboot(self) -> None:
        """A changed boot time flags a reboot; clearing resets it."""

        identity = ARDeviceIdentity()
        identity.update_boottime(datetime(2026, 1, 1, tzinfo=UTC))

        identity.update_boottime(datetime(2026, 1, 2, tzinfo=UTC))
        assert identity.rebooted is True

        identity.clear_rebooted()
        assert identity.rebooted is False
