"""Tests for the network source dispatch."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from asusrouter.const import AR_CALL_GET_STATE, AR_CALL_TRANSLATE_STATE
from asusrouter.modules.network.enums import ARNetworkField, ARNetworkType
from asusrouter.modules.network.source import (
    ARNetworkSource,
    ARNetworkSourceUniversal,
    _sdn_supported,
    get_state,
    translate_state,
)
from asusrouter.modules.support.flag import ARSupportType
from asusrouter.modules.wifi import ARWiFiBand
from asusrouter.registry import ARCallableRegistry as ARCallReg


def _enc(text: str) -> str:
    """Char-encode `<`/`>` as the router does."""

    return text.replace("<", "&#60").replace(">", "&#62")


def _identity(*, sdn_rules: Any = None, wifi: dict | None = None) -> Any:
    """Build a stub identity with a support map and wifi map."""

    support = (
        {} if sdn_rules is None else {ARSupportType.SDN_MAX_RULES: sdn_rules}
    )
    return SimpleNamespace(support=support, wifi=wifi or {})


class TestSdnSupported:
    """Tests for _sdn_supported."""

    @pytest.mark.parametrize(
        ("sdn_rules", "expected"),
        [(19, True), ("9", True), (0, False), (None, False)],
    )
    def test_flag(self, sdn_rules: Any, expected: bool) -> None:
        """A positive MaxRule_SDN means SDN is supported."""

        assert _sdn_supported(_identity(sdn_rules=sdn_rules)) is expected

    def test_no_identity(self) -> None:
        """No identity means no SDN."""

        assert _sdn_supported(None) is False


class TestGetState:
    """Tests for get_state backend selection."""

    async def test_sdn_backend(self) -> None:
        """An SDN device fetches sdn_rl first."""

        callback = AsyncMock(return_value={})
        await get_state(
            callback,
            ARNetworkSourceUniversal,
            identity=_identity(sdn_rules=19),
        )

        assert "nvram_get(sdn_rl)" in callback.call_args.kwargs["request"]

    async def test_legacy_backend(self) -> None:
        """A non-SDN device fetches per-band nvram."""

        callback = AsyncMock(return_value={})
        await get_state(
            callback,
            ARNetworkSourceUniversal,
            identity=_identity(wifi={ARWiFiBand.BAND_2G1: 0}),
        )

        assert "nvram_get(wl0_ssid)" in callback.call_args.kwargs["request"]


class TestTranslateState:
    """Tests for translate_state backend selection."""

    @pytest.mark.parametrize("data", [None, "text", 42])
    def test_bad_data(self, data: Any) -> None:
        """Non-dict data yields an empty result."""

        assert translate_state(data) == {}

    def test_sdn_data(self) -> None:
        """Data with sdn_rl uses the SDN parser."""

        data = {"sdn_rl": _enc("<1>MAINFH>1>0>0>2"), "apm2_ssid": "Net"}
        result = translate_state(
            data, identity=_identity(wifi={ARWiFiBand.BAND_2G1: 0})
        )

        assert ARNetworkType.MAINFH in result

    def test_legacy_data(self) -> None:
        """Data without sdn_rl uses the legacy parser."""

        data = {"wl0_ssid": "Net", "wl0_radio": "1"}
        result = translate_state(
            data, identity=_identity(wifi={ARWiFiBand.BAND_2G1: 0})
        )

        net = result[ARNetworkType.MAINFH][0]
        assert net[ARNetworkField.SSID].value == "Net"


def test_source_is_registered() -> None:
    """The source registers get_state and translate_state."""

    assert (
        ARCallReg.get_callable(ARNetworkSourceUniversal, AR_CALL_GET_STATE)
        is get_state
    )
    assert (
        ARCallReg.get_callable(ARNetworkSource, AR_CALL_TRANSLATE_STATE)
        is translate_state
    )
