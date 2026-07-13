"""Tests for the wifi data source."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from asusrouter.const import AR_CALL_GET_STATE, AR_CALL_TRANSLATE_STATE
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.wifi import ARWiFiBand, ARWiFiBandwidth, ARWiFiField
from asusrouter.modules.wifi.source import (
    ARWiFiSource,
    ARWiFiSourceUniversal,
    _array_at,
    _build_request,
    get_state,
    translate_state,
)
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.identifiers import MacAddress

_MAC = "AA:BB:CC:00:11:22"

# Router with three radios: 2g1 (unit 0), 5g1 (unit 1), 6g1 (unit 2)
_WIFI = {
    ARWiFiBand.BAND_2G1: 0,
    ARWiFiBand.BAND_5G1: 1,
    ARWiFiBand.BAND_6G1: 2,
}


def _identity(wifi: dict[ARWiFiBand, int] | None) -> Any:
    """Build a stub identity carrying a wifi map."""

    return SimpleNamespace(wifi=wifi)


_RESPONSE: dict[str, Any] = {
    "wl_control_channel": ["6", "100", "5"],
    "2g1_nmode_x": "0",
    "2g1_bw": "5",
    "2g1_chanspec": "6u",
    "2g1_nctrlsb": "",
    "2g1_bw_160": "0",
    "2g1_bw_240": "",
    "2g1_11be": "1",
    "wl0_radio": "1",
    "wl0_country_code": "US",
    "wl0_version": "17.10",
    "wl0_hwaddr": _MAC,
}


class TestArrayAt:
    """Tests for _array_at."""

    @pytest.mark.parametrize(
        ("value", "index", "expected"),
        [
            (["a", "b", "c"], 1, "b"),
            (["a"], 5, None),
            (["a"], -1, None),
            ("not a list", 0, None),
            (None, 0, None),
        ],
    )
    def test_index(self, value: Any, index: int, expected: Any) -> None:
        """Returns the indexed item or None."""

        assert _array_at(value, index) == expected


class TestBuildRequest:
    """Tests for _build_request."""

    def test_no_identity(self) -> None:
        """No identity yields no request."""

        assert _build_request(None) is None

    def test_empty_wifi(self) -> None:
        """An empty wifi map yields no request."""

        assert _build_request(_identity({})) is None

    def test_builds_request(self) -> None:
        """The request carries the hooks and per-band/unit nvram keys."""

        request = _build_request(_identity({ARWiFiBand.BAND_2G1: 0}))

        assert request is not None
        assert request.startswith("hook=wl_control_channel();")
        assert "nvram_get(2g1_bw)" in request
        assert "nvram_get(2g1_chanspec)" in request
        assert "nvram_get(wl0_hwaddr)" in request


class TestGetState:
    """Tests for get_state."""

    async def test_no_identity(self) -> None:
        """No identity yields no data without calling back."""

        callback = AsyncMock()
        result = await get_state(callback, ARWiFiSourceUniversal)

        assert result == {}
        callback.assert_not_called()

    async def test_fetches(self) -> None:
        """The built request is sent to the appGet endpoint."""

        callback = AsyncMock(return_value={"ok": True})
        result = await get_state(
            callback,
            ARWiFiSourceUniversal,
            identity=_identity({ARWiFiBand.BAND_2G1: 0}),
        )

        assert result == {"ok": True}
        args = callback.call_args.kwargs
        assert args["endpoint"] is AREndpoint.FETCH_DATA
        assert args["request"].startswith("hook=")


class TestTranslateState:
    """Tests for translate_state."""

    @pytest.mark.parametrize("data", [None, "text", 42, []])
    def test_bad_data(self, data: Any) -> None:
        """Non-dict data yields an empty result."""

        assert translate_state(data, identity=_identity(_WIFI)) == {}

    def test_no_identity(self) -> None:
        """Missing identity yields an empty result."""

        assert translate_state(_RESPONSE, identity=None) == {}

    def test_empty_wifi(self) -> None:
        """An empty wifi map yields an empty result."""

        assert translate_state(_RESPONSE, identity=_identity({})) == {}

    def test_full_band(self) -> None:
        """A fully populated band maps every present radio field."""

        result = translate_state(_RESPONSE, identity=_identity(_WIFI))
        band = result[ARWiFiBand.BAND_2G1]

        assert band[ARWiFiField.CHANNEL] == 6
        assert band[ARWiFiField.WIRELESS_MODE] == 0
        assert band[ARWiFiField.BANDWIDTH] is ARWiFiBandwidth.WIDTH_160
        assert band[ARWiFiField.CHANNEL_SPEC] == "6u"
        assert band[ARWiFiField.ENABLE_160MHZ] is False
        assert band[ARWiFiField.WIFI7] is True
        assert band[ARWiFiField.STATE] is True
        assert band[ARWiFiField.COUNTRY] == "US"
        assert band[ARWiFiField.DRIVER] == "17.10"
        assert band[ARWiFiField.MAC] == MacAddress(_MAC)

    def test_empty_fields_skipped(self) -> None:
        """Absent/empty raw values are omitted from the band dict."""

        band = translate_state(_RESPONSE, identity=_identity(_WIFI))[
            ARWiFiBand.BAND_2G1
        ]

        assert ARWiFiField.SIDE_BAND not in band
        assert ARWiFiField.ENABLE_240MHZ not in band

    def test_hook_only_band(self) -> None:
        """A band with only hook data still maps the live channel."""

        result = translate_state(_RESPONSE, identity=_identity(_WIFI))
        band = result[ARWiFiBand.BAND_5G1]

        assert band == {ARWiFiField.CHANNEL: 100}

    def test_bandless_unit_omitted(self) -> None:
        """A unit beyond the hook arrays with no nvram is omitted."""

        result = translate_state(
            _RESPONSE, identity=_identity({ARWiFiBand.BAND_6G2: 9})
        )

        assert result == {}


def test_source_is_registered() -> None:
    """The source registers get_state and translate_state."""

    assert (
        ARCallReg.get_callable(ARWiFiSourceUniversal, AR_CALL_GET_STATE)
        is get_state
    )
    assert (
        ARCallReg.get_callable(ARWiFiSource, AR_CALL_TRANSLATE_STATE)
        is translate_state
    )
