"""Tests for the LED data source."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from asusrouter.modules.led.enums import ARLedField
from asusrouter.modules.led.source import (
    ARLedSourceUniversal,
    get_state,
    translate_state,
)
from asusrouter.modules.nvram import ARNvramType


class TestGetState:
    """Tests for get_state."""

    async def test_fetches_via_nvram(self) -> None:
        """The LED item is requested from the NVRAM module."""

        values = {ARNvramType.LED: "1"}
        get_data = AsyncMock(return_value=values)
        callback = AsyncMock()

        result = await get_state(
            callback, ARLedSourceUniversal, get_data_callback=get_data
        )

        assert result == values
        callback.assert_not_awaited()
        requested = get_data.await_args.args[0]
        assert set(requested) == {ARNvramType.LED}

    async def test_no_get_data_callback(self) -> None:
        """Without a data callback nothing is fetched."""

        callback = AsyncMock()
        result = await get_state(callback, ARLedSourceUniversal)
        assert result == {}
        callback.assert_not_awaited()

    async def test_non_dict_response(self) -> None:
        """A non-dict response is normalized to an empty dict."""

        get_data = AsyncMock(return_value=None)
        result = await get_state(
            AsyncMock(), ARLedSourceUniversal, get_data_callback=get_data
        )
        assert result == {}


class TestTranslateState:
    """Tests for translate_state."""

    @pytest.mark.parametrize("data", [None, {}, "text", []])
    def test_empty(self, data: Any) -> None:
        """Non-dict or empty data yields an empty result."""

        assert translate_state(data) == {}

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [("1", True), ("0", False), (1, True), (0, False)],
    )
    def test_state(self, raw: Any, expected: bool) -> None:
        """The led_val maps to a boolean state."""

        result = translate_state({ARNvramType.LED: raw})
        assert result[ARLedField.STATE] is expected

    def test_unparseable(self) -> None:
        """An unparseable value yields a None state."""

        result = translate_state({ARNvramType.LED: "maybe"})
        assert result[ARLedField.STATE] is None
