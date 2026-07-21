"""Tests for the Aura data source."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from asusrouter.modules.aura.enums import (
    ARAuraCapability,
    ARAuraField,
    ARAuraScheme,
)
from asusrouter.modules.aura.source import (
    ARAuraSourceUniversal,
    fetch_state,
    translate_state,
)
from asusrouter.modules.nvram import (
    ARNvramIndexSource,
    ARNvramIndexType,
    ARNvramType,
)
from asusrouter.modules.support.flag import ARSupportType


def _rgb(code: int) -> ARNvramIndexSource:
    """Build the indexed color source for a scheme code."""

    return ARNvramIndexSource(ARNvramIndexType.AURA_RGB, code)


def _identity(*, aura: bool = True, night: bool = False) -> SimpleNamespace:
    """Build a fake identity exposing an Aura support map."""

    capabilities = {ARAuraCapability.NIGHT_MODE: True} if night else {}
    return SimpleNamespace(
        support={
            ARSupportType.AURA: aura,
            ARSupportType.AURA_CAPABILITIES: capabilities,
        }
    )


class TestGetState:
    """Tests for fetch_state."""

    async def test_no_identity(self) -> None:
        """No identity means Aura is not supported."""

        callback = AsyncMock()
        assert await fetch_state(callback, ARAuraSourceUniversal) == {}
        callback.assert_not_awaited()

    async def test_unsupported(self) -> None:
        """An identity without Aura support fetches nothing."""

        callback = AsyncMock()
        result = await fetch_state(
            callback, ARAuraSourceUniversal, identity=_identity(aura=False)
        )
        assert result == {}
        callback.assert_not_awaited()

    async def test_supported_fetches_via_nvram(self) -> None:
        """A supported device requests the Aura items from the NVRAM module."""

        values = {ARNvramType.AURA: "1"}
        get_data = AsyncMock(return_value=values)
        callback = AsyncMock()

        result = await fetch_state(
            callback,
            ARAuraSourceUniversal,
            fetch_data_callback=get_data,
            identity=_identity(),
        )

        assert result == values
        callback.assert_not_awaited()
        request = get_data.await_args.args[0]
        assert ARNvramType.AURA in request
        assert ARNvramType.AURA_SCHEME in request
        assert _rgb(0) in request
        assert _rgb(7) in request
        assert ARNvramType.AURA_NIGHT_MODE in request  # flag read
        # Night colors are firmware-dead, not fetched
        assert ARNvramType.AURA_NIGHT_RGB not in request

    async def test_no_get_data_callback(self) -> None:
        """Without a data callback nothing is fetched."""

        callback = AsyncMock()
        result = await fetch_state(
            callback, ARAuraSourceUniversal, identity=_identity()
        )
        assert result == {}
        callback.assert_not_awaited()

    async def test_non_dict_response(self) -> None:
        """A non-dict response is normalized to an empty dict."""

        get_data = AsyncMock(return_value=None)
        result = await fetch_state(
            AsyncMock(),
            ARAuraSourceUniversal,
            fetch_data_callback=get_data,
            identity=_identity(),
        )
        assert result == {}


class TestTranslateState:
    """Tests for translate_state."""

    @pytest.mark.parametrize("data", [None, {}, "text", []])
    def test_empty(self, data: Any) -> None:
        """Non-dict or empty data yields an empty result."""

        assert translate_state(data) == {}

    def test_basic_fields(self) -> None:
        """Core fields are parsed from nvram."""

        data = {
            "AllLED": "1",
            "ledg_scheme": "2",
            "ledg_scheme_old": "3",
            "ledg_count": "4",
        }
        result = translate_state(data, identity=_identity())

        assert result[ARAuraField.STATE] is True
        assert result[ARAuraField.SCHEME] is ARAuraScheme.STATIC
        assert result[ARAuraField.SCHEME_PREV] is ARAuraScheme.BREATHING
        assert result[ARAuraField.ZONES] == 4

    def test_off_forces_state_off(self) -> None:
        """An OFF scheme reports the master state as off."""

        data = {"AllLED": "1", "ledg_scheme": "0"}
        result = translate_state(data, identity=_identity())
        assert result[ARAuraField.STATE] is False

    def test_zones_fallback_to_static(self) -> None:
        """Without ledg_count, zones come from the static effect length."""

        data = {
            "ledg_scheme": "2",
            _rgb(2): "10,0,64,64,0,32",  # two colors
        }
        result = translate_state(data, identity=_identity())
        assert result[ARAuraField.ZONES] == 2

    def test_day_colors_parsed(self) -> None:
        """Day colors are grouped per scheme."""

        data = {"ledg_scheme": "2", _rgb(2): "10,0,64"}
        result = translate_state(data, identity=_identity())
        colors = result[ARAuraField.COLORS]
        assert ARAuraScheme.STATIC in colors
        assert len(colors[ARAuraScheme.STATIC]) == 1

    def test_night_absent_without_identity(self) -> None:
        """Night fields are omitted when no identity is provided."""

        data = {"ledg_scheme": "2", "ledg_night_mode": "1"}
        result = translate_state(data)
        assert ARAuraField.NIGHT_MODE not in result

    def test_night_absent_without_support(self) -> None:
        """The night mode flag is omitted when night mode is unsupported."""

        data = {"ledg_scheme": "2", "ledg_night_mode": "1"}
        result = translate_state(data, identity=_identity(night=False))
        assert ARAuraField.NIGHT_MODE not in result

    def test_night_present_with_support(self) -> None:
        """The night mode flag appears when supported; colors are not read."""

        data = {"ledg_scheme": "2", "ledg_night_mode": "1"}
        result = translate_state(data, identity=_identity(night=True))
        assert result[ARAuraField.NIGHT_MODE] is True
        # Night colors are firmware-dead and never emitted
        assert ARAuraField.NIGHT_COLORS not in result

    def test_sdn_not_emitted(self) -> None:
        """SDN is not exposed (untestable niche feature)."""

        data = {"ledg_scheme": "2", "ledg_sdn": "1<0<0"}
        result = translate_state(data, identity=_identity())
        assert ARAuraField.SDN not in result

    def test_active_summary(self) -> None:
        """A color scheme reports a blended active color and brightness."""

        data = {"ledg_scheme": "2", _rgb(2): "10,0,64,64,0,32"}
        result = translate_state(data, identity=_identity())
        assert ARAuraField.COLOR in result
        assert ARAuraField.BRIGHTNESS in result

    def test_no_active_summary_for_non_color_scheme(self) -> None:
        """A non-color scheme omits the active color summary."""

        data = {"ledg_scheme": "5", _rgb(5): "10,0,64"}  # rainbow
        result = translate_state(data, identity=_identity())
        assert ARAuraField.COLOR not in result
