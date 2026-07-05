"""Tests for the network legacy backend."""

from __future__ import annotations

from unittest.mock import AsyncMock

from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.network import legacy
from asusrouter.modules.network.enums import ARNetworkField, ARNetworkType
from asusrouter.modules.wifi import ARWiFiAuthMode, ARWiFiBand
from asusrouter.tools.identifiers import MacAddress, Password, Ssid

_MAC = "AA:BB:CC:DD:EE:FF"
_WIFI = {ARWiFiBand.BAND_2G1: 0, ARWiFiBand.BAND_5G1: 1}

# Main "HomeNet" shared across both bands (smart connect); one 2.4G guest
_DATA = {
    "wl0_ssid": "HomeNet",
    "wl0_wpa_psk": "pass1234",
    "wl0_auth_mode_x": "psk2",
    "wl0_crypto": "aes",
    "wl0_closed": "1",
    "wl0_radio": "1",
    "wl0_macmode": "disabled",
    "wl0_maclist_x": f"&#60{_MAC}&#62",
    "wl0_ap_isolate": "0",
    "wl1_ssid": "HomeNet",
    "wl1_wpa_psk": "pass1234",
    "wl1_auth_mode_x": "psk2",
    "wl1_crypto": "aes",
    "wl1_radio": "1",
    "wl1.1_ssid": "",
    "wl0.1_ssid": "Guest",
    "wl0.1_wpa_psk": "guestpw",
    "wl0.1_auth_mode_x": "open",
    "wl0.1_bss_enabled": "1",
    "wl0.1_lanaccess": "off",
    "wl0.1_expire": "3600",
    "wl0.1_expire_tmp": "1200",
}


class TestFetch:
    """Tests for the legacy fetch."""

    async def test_no_wifi(self) -> None:
        """No wifi map returns None without a fetch."""

        callback = AsyncMock()
        assert await legacy.fetch(callback, {}) is None
        callback.assert_not_called()

    async def test_request(self) -> None:
        """The request covers main and guest keys for every band."""

        callback = AsyncMock(return_value={"wl0_ssid": "X"})
        await legacy.fetch(callback, _WIFI)

        args = callback.call_args.kwargs
        assert args["endpoint"] is AREndpoint.FETCH_DATA
        assert "nvram_get(wl0_ssid)" in args["request"]
        assert "nvram_get(wl1_ssid)" in args["request"]
        assert "nvram_get(wl0.1_ssid)" in args["request"]


class TestTranslate:
    """Tests for legacy.translate."""

    def test_main_grouped_by_ssid(self) -> None:
        """The shared main SSID groups both bands into one network."""

        main = legacy.translate(_DATA, _WIFI)[ARNetworkType.MAINFH]

        assert len(main) == 1
        net = main[0]
        assert net[ARNetworkField.SSID] == Ssid("HomeNet")
        assert net[ARNetworkField.ENABLED] is True
        assert net[ARNetworkField.HIDDEN] is True
        assert net[ARNetworkField.PASSWORD] == Password("pass1234")
        assert net[ARNetworkField.BANDS] == [
            ARWiFiBand.BAND_2G1,
            ARWiFiBand.BAND_5G1,
        ]
        assert net[ARNetworkField.MAC_FILTER_LIST] == [MacAddress(_MAC)]
        security = net[ARNetworkField.SECURITY]
        assert (
            security[ARWiFiBand.BAND_2G1][ARNetworkField.AUTH]
            is ARWiFiAuthMode.PSK2
        )
        assert security[ARWiFiBand.BAND_5G1][ARNetworkField.CIPHER] == "aes"

    def test_guest(self) -> None:
        """A guest slot becomes a GUEST network on its band."""

        guests = legacy.translate(_DATA, _WIFI)[ARNetworkType.GUEST]

        assert len(guests) == 1
        guest = guests[0]
        assert guest[ARNetworkField.SSID] == Ssid("Guest")
        assert guest[ARNetworkField.ENABLED] is True
        assert guest[ARNetworkField.BANDS] == [ARWiFiBand.BAND_2G1]
        assert guest[ARNetworkField.LAN_ACCESS] is False
        assert guest[ARNetworkField.EXPIRE] == 3600
        assert guest[ARNetworkField.EXPIRE_REMAINING] == 1200
        assert (
            guest[ARNetworkField.SECURITY][ARWiFiBand.BAND_2G1][
                ARNetworkField.AUTH
            ]
            is ARWiFiAuthMode.OPEN
        )

    def test_main_has_no_guest_fields(self) -> None:
        """Guest-only nvram is absent on the main network."""

        main = legacy.translate(_DATA, _WIFI)[ARNetworkType.MAINFH][0]

        assert ARNetworkField.LAN_ACCESS not in main
        assert ARNetworkField.EXPIRE not in main
        assert ARNetworkField.EXPIRE_REMAINING not in main

    def test_split_ssid(self) -> None:
        """Different per-band SSIDs become separate networks."""

        data = {
            "wl0_ssid": "Net2G",
            "wl0_radio": "1",
            "wl1_ssid": "Net5G",
            "wl1_radio": "1",
        }
        main = legacy.translate(data, _WIFI)[ARNetworkType.MAINFH]

        assert {n[ARNetworkField.SSID] for n in main} == {
            Ssid("Net2G"),
            Ssid("Net5G"),
        }

    def test_no_networks(self) -> None:
        """No configured SSIDs yield an empty result."""

        assert legacy.translate({}, _WIFI) == {}
