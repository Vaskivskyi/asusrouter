"""Tests for the network legacy backend."""

from __future__ import annotations

from unittest.mock import AsyncMock

from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.network import legacy
from asusrouter.modules.network.enums import (
    ARNetworkBackend,
    ARNetworkField,
    ARNetworkType,
)
from asusrouter.modules.network.handle import ARNetworkHandle
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
    "wl0.1_bw_enabled": "1",
    "wl0.1_bw_dl": "5120",
    "wl0.1_bw_ul": "2048",
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
        assert guest[ARNetworkField.BANDWIDTH_LIMIT_DOWNLOAD] == 5120 * 1024
        assert guest[ARNetworkField.BANDWIDTH_LIMIT_UPLOAD] == 2048 * 1024
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
        assert ARNetworkField.BANDWIDTH_LIMIT_DOWNLOAD not in main

    def test_main_enabled_if_any_band_on(self) -> None:
        """A shared main stays enabled while any band radio is on."""

        data = dict(_DATA)
        data["wl0_radio"] = "0"  # 2.4G off, 5G still on
        net = legacy.translate(data, _WIFI)[ARNetworkType.MAINFH][0]

        assert net[ARNetworkField.ENABLED] is True

    def test_main_disabled_if_all_bands_off(self) -> None:
        """A shared main is disabled only when every band radio is off."""

        data = dict(_DATA)
        data["wl0_radio"] = "0"
        data["wl1_radio"] = "0"
        net = legacy.translate(data, _WIFI)[ARNetworkType.MAINFH][0]

        assert net[ARNetworkField.ENABLED] is False

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

    def test_main_handle(self) -> None:
        """The main network carries a legacy handle with per-band units."""

        main = legacy.translate(_DATA, _WIFI)[ARNetworkType.MAINFH][0]
        assert main[ARNetworkField.HANDLE] == ARNetworkHandle(
            backend=ARNetworkBackend.LEGACY, units=((0, None), (1, None))
        )

    def test_guest_handle(self) -> None:
        """The guest network carries a legacy handle with its unit and slot."""

        guest = legacy.translate(_DATA, _WIFI)[ARNetworkType.GUEST][0]
        assert guest[ARNetworkField.HANDLE] == ARNetworkHandle(
            backend=ARNetworkBackend.LEGACY, units=((0, 1),)
        )


class TestBuildTogglePayload:
    """Tests for build_toggle_payload."""

    def test_main_toggles_radio(self) -> None:
        """A main handle toggles the per-band radio via restart_wireless."""

        handle = ARNetworkHandle(
            backend=ARNetworkBackend.LEGACY, units=((0, None), (1, None))
        )
        rc_service, arguments = legacy.build_toggle_payload(handle, False)

        assert rc_service == "restart_wireless"
        assert arguments == {"wl0_radio": 0, "wl1_radio": 0}

    def test_guest_enable_clears_expire(self) -> None:
        """Enabling a guest sets bss_enabled and clears the time limit."""

        handle = ARNetworkHandle(
            backend=ARNetworkBackend.LEGACY, units=((0, 1),)
        )
        rc_service, arguments = legacy.build_toggle_payload(handle, True)

        assert rc_service == "restart_wireless;restart_firewall"
        assert arguments == {
            "wl0.1_bss_enabled": 1,
            "wl0.1_expire": 0,
        }

    def test_guest_disable_keeps_expire_untouched(self) -> None:
        """Disabling a guest clears bss_enabled without touching expire."""

        handle = ARNetworkHandle(
            backend=ARNetworkBackend.LEGACY, units=((0, 1),)
        )
        _, arguments = legacy.build_toggle_payload(handle, False)

        assert arguments == {"wl0.1_bss_enabled": 0}
