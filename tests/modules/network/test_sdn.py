"""Tests for the network SDN backend."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.network import sdn
from asusrouter.modules.network.enums import (
    ARNetworkField,
    ARNetworkSchedule,
    ARNetworkType,
)
from asusrouter.modules.wifi import ARWiFiAuthMode, ARWiFiBand
from asusrouter.tools.identifiers import MacAddress, Password, Ssid

_MAC = "AA:BB:CC:DD:EE:FF"
_BANDS = [ARWiFiBand.BAND_2G1, ARWiFiBand.BAND_5G1, ARWiFiBand.BAND_6G1]


def _enc(text: str) -> str:
    """Char-encode `<`/`>` as the router does."""

    return text.replace("<", "&#60").replace(">", "&#62")


# idx 0 (skipped), MAINFH -> apm2, Customized -> apg4
_SDN_RL = _enc("<0>DEFAULT>1>0>0>0<1>MAINFH>1>0>0>2<3>Customized>1>0>0>4")

# security: band 3 (2.4+5) psk2sae, band 16 (6G) sae
_SECURITY = _enc("<3>psk2sae>aes>secret>0<16>sae>aes>secret>0")

_AP_DATA = {
    "sdn_rl": _SDN_RL,
    "apm2_enable": "1",
    "apm2_ssid": "MainNet",
    "apm2_hide_ssid": "0",
    "apm2_security": _SECURITY,
    "apm2_ap_isolate": "0",
    "apm2_macmode": "disabled",
    "apm2_mlo": "2",
    "apm2_maclist": _enc(f"<{_MAC}>"),
    "apm2_dut_list": _enc("<*>19>"),
    "apm2_11be": "1",
    "apm2_timesched": "1",
    "apm2_sched": "W1E2",
    "apg4_enable": "1",
    "apg4_ssid": "Guest",
    "apg4_security": _enc("<3>psk2>aes>guestpass>0"),
    "apg4_dut_list": _enc("<*>1>"),
    "apg4_bw_limit": _enc("<1>2048>5120"),
}


class TestParseSdnRl:
    """Tests for _parse_sdn_rl."""

    def test_profiles_and_prefix(self) -> None:
        """Profiles parse with prefix and enable; idx 0 is skipped."""

        assert sdn._parse_sdn_rl(_SDN_RL) == [
            ("MAINFH", "apm", 2, True),
            ("Customized", "apg", 4, True),
        ]

    @pytest.mark.parametrize("raw", [None, "", _enc("<1>X>1")])
    def test_bad_rows(self, raw: Any) -> None:
        """Short or empty rule-lists yield no profiles."""

        assert sdn._parse_sdn_rl(raw) == []

    def test_non_numeric_apg_idx(self) -> None:
        """A non-numeric apg index is skipped."""

        assert sdn._parse_sdn_rl(_enc("<1>X>1>0>0>z")) == []


class TestParseSecurity:
    """Tests for _parse_security."""

    def test_password_and_per_band(self) -> None:
        """Password is network-wide; auth is per-band (6G=SAE)."""

        password, per_band = sdn._parse_security(_SECURITY, _BANDS)

        assert password == Password("secret")
        assert (
            per_band[ARWiFiBand.BAND_2G1][ARNetworkField.AUTH]
            is ARWiFiAuthMode.PSK2SAE
        )
        assert (
            per_band[ARWiFiBand.BAND_6G1][ARNetworkField.AUTH]
            is ARWiFiAuthMode.SAE
        )
        assert per_band[ARWiFiBand.BAND_2G1][ARNetworkField.CIPHER] == "aes"
        assert ARNetworkField.PASSWORD not in per_band[ARWiFiBand.BAND_2G1]

    def test_band_without_entry(self) -> None:
        """A band with no matching entry is omitted; password still read."""

        password, per_band = sdn._parse_security(
            _SECURITY, [ARWiFiBand.BAND_5G2]
        )
        assert per_band == {}
        assert password == Password("secret")

    def test_no_password(self) -> None:
        """An empty passphrase yields no password."""

        password, _ = sdn._parse_security(_enc("<3>open>aes>>0"), _BANDS)
        assert password is None


class TestDutBands:
    """Tests for _dut_bands."""

    def test_union(self) -> None:
        """The band bitmask union maps to the device bands."""

        assert sdn._dut_bands(_enc("<*>19>"), _BANDS) == _BANDS

    def test_partial(self) -> None:
        """Only the bits present resolve to bands."""

        assert sdn._dut_bands(_enc("<*>1>"), _BANDS) == [ARWiFiBand.BAND_2G1]

    def test_empty(self) -> None:
        """No dut list yields no bands."""

        assert sdn._dut_bands("", _BANDS) == []


class TestSchedule:
    """Tests for _schedule."""

    def test_disabled(self) -> None:
        """No scheduling yields no fields."""

        assert sdn._schedule("0", "", "") == {}

    def test_weekly(self) -> None:
        """A weekly schedule keeps the raw schedule string."""

        result = sdn._schedule("1", "W1E2", "")
        assert result[ARNetworkField.SCHEDULE_MODE] is (
            ARNetworkSchedule.SCHEDULED
        )
        assert result[ARNetworkField.SCHEDULE] == "W1E2"
        assert ARNetworkField.EXPIRY not in result

    def test_one_time(self) -> None:
        """A one-time schedule keeps the raw expiry string."""

        result = sdn._schedule("2", "", "100,200")
        assert result[ARNetworkField.SCHEDULE_MODE] is (
            ARNetworkSchedule.ONE_TIME
        )
        assert result[ARNetworkField.EXPIRY] == "100,200"
        assert ARNetworkField.SCHEDULE not in result


class TestBandwidth:
    """Tests for _bandwidth."""

    def test_enabled(self) -> None:
        """An enabled limiter yields both rates in bits/s."""

        assert sdn._bandwidth(_enc("<1>2048>5120")) == {
            ARNetworkField.BANDWIDTH_LIMIT_DOWNLOAD: 5120 * 1024,
            ARNetworkField.BANDWIDTH_LIMIT_UPLOAD: 2048 * 1024,
        }

    @pytest.mark.parametrize("raw", [_enc("<0>>"), "", None])
    def test_disabled(self, raw: Any) -> None:
        """A disabled or empty limiter yields no fields."""

        assert sdn._bandwidth(raw) == {}


class TestFetch:
    """Tests for the two-step SDN fetch."""

    async def test_two_step(self) -> None:
        """sdn_rl is fetched first, then the referenced AP groups."""

        callback = AsyncMock(
            side_effect=[
                {"sdn_rl": _SDN_RL},
                {"apm2_ssid": "MainNet", "apg4_ssid": "Guest"},
            ]
        )
        result = await sdn.fetch(callback)

        assert result["sdn_rl"] == _SDN_RL
        assert result["apm2_ssid"] == "MainNet"
        assert callback.call_count == 2
        second = callback.call_args_list[1].kwargs
        assert second["endpoint"] is AREndpoint.FETCH_DATA
        assert "nvram_get(apm2_ssid)" in second["request"]

    async def test_no_sdn_rl(self) -> None:
        """A missing sdn_rl returns None without a second fetch."""

        callback = AsyncMock(return_value={})
        assert await sdn.fetch(callback) is None
        assert callback.call_count == 1

    async def test_no_profiles(self) -> None:
        """An empty sdn_rl returns only the raw list, no second fetch."""

        callback = AsyncMock(return_value={"sdn_rl": ""})
        assert await sdn.fetch(callback) == {"sdn_rl": ""}
        assert callback.call_count == 1


class TestTranslate:
    """Tests for sdn.translate."""

    def test_grouped_by_type(self) -> None:
        """Networks are grouped by their SDN type."""

        result = sdn.translate(_AP_DATA, _BANDS)
        assert set(result) == {
            ARNetworkType.MAINFH,
            ARNetworkType.CUSTOMIZED,
        }

    def test_main_network(self) -> None:
        """The main network maps every field."""

        main = sdn.translate(_AP_DATA, _BANDS)[ARNetworkType.MAINFH][0]

        assert main[ARNetworkField.SSID] == Ssid("MainNet")
        assert main[ARNetworkField.ENABLED] is True
        assert main[ARNetworkField.HIDDEN] is False
        assert main[ARNetworkField.WIFI7] is True
        assert main[ARNetworkField.AP_ISOLATE] is False
        assert main[ARNetworkField.MLO] == 2
        assert (
            main[ARNetworkField.SCHEDULE_MODE] is ARNetworkSchedule.SCHEDULED
        )
        assert main[ARNetworkField.SCHEDULE] == "W1E2"
        assert main[ARNetworkField.MAC_FILTER_LIST] == [MacAddress(_MAC)]
        assert main[ARNetworkField.BANDS] == _BANDS
        assert main[ARNetworkField.PASSWORD] == Password("secret")
        assert ARNetworkField.BANDWIDTH_LIMIT_DOWNLOAD not in main
        security = main[ARNetworkField.SECURITY]
        assert (
            security[ARWiFiBand.BAND_6G1][ARNetworkField.AUTH]
            is ARWiFiAuthMode.SAE
        )

    def test_security_limited_to_bound_bands(self) -> None:
        """Security covers only the bands the network is bound to."""

        guest = sdn.translate(_AP_DATA, _BANDS)[ARNetworkType.CUSTOMIZED][0]

        assert guest[ARNetworkField.BANDS] == [ARWiFiBand.BAND_2G1]
        assert set(guest[ARNetworkField.SECURITY]) == {ARWiFiBand.BAND_2G1}
        assert ARNetworkField.SCHEDULE_MODE not in guest
        assert guest[ARNetworkField.BANDWIDTH_LIMIT_DOWNLOAD] == 5120 * 1024
        assert guest[ARNetworkField.BANDWIDTH_LIMIT_UPLOAD] == 2048 * 1024

    def test_enabled_requires_sdn_enable(self) -> None:
        """A network off at the SDN level is not enabled."""

        data = {"sdn_rl": _enc("<1>MAINFH>0>0>0>2"), "apm2_enable": "1"}
        net = sdn.translate(data, _BANDS)[ARNetworkType.MAINFH][0]
        assert net[ARNetworkField.ENABLED] is False

    def test_no_bands_without_identity(self) -> None:
        """With no device bands, band-derived fields are omitted."""

        main = sdn.translate(_AP_DATA, [])[ARNetworkType.MAINFH][0]
        assert main[ARNetworkField.SSID] == Ssid("MainNet")
        assert ARNetworkField.BANDS not in main
        assert ARNetworkField.SECURITY not in main
