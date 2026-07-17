"""Tests for the block-all-devices data source."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from asusrouter.modules.nvram import ARNvramType
from asusrouter.modules.parental_control.block_all.source import (
    ARBlockAllSourceUniversal,
    fetch_state,
    translate_state,
)


class TestGetState:
    """Tests for fetch_state."""

    async def test_fetches_via_nvram(self) -> None:
        """The block-all key is requested from the NVRAM module."""

        get_data = AsyncMock(return_value={"MULTIFILTER_BLOCK_ALL": "1"})
        result = await fetch_state(
            AsyncMock(),
            ARBlockAllSourceUniversal,
            fetch_data_callback=get_data,
        )

        assert result == {"MULTIFILTER_BLOCK_ALL": "1"}
        assert (
            get_data.await_args.args[0]
            is ARNvramType.PARENTAL_CONTROL_BLOCK_ALL
        )

    async def test_no_get_data_callback(self) -> None:
        """Without a data callback nothing is fetched."""

        result = await fetch_state(AsyncMock(), ARBlockAllSourceUniversal)
        assert result == {}


class TestTranslateState:
    """Tests for translate_state."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [("1", True), ("0", False), (None, False)],
    )
    def test_bool(self, raw: Any, expected: bool) -> None:
        """The switch translates to a boolean."""

        assert translate_state({"MULTIFILTER_BLOCK_ALL": raw}) is expected

    @pytest.mark.parametrize("data", [None, "text", []])
    def test_non_dict(self, data: Any) -> None:
        """A non-dict payload reads as off."""

        assert translate_state(data) is False
