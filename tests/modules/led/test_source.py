"""Tests for the LED data source."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from asusrouter.modules.aimesh.source import ARAiMeshSourceUniversal
from asusrouter.modules.aimesh.topology import ARAiMeshNode, ARAiMeshTopology
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.led.enums import ARLedField
from asusrouter.modules.led.source import (
    ARLedSourceUniversal,
    fetch_state,
    translate_state,
)
from asusrouter.modules.nvram import ARNvramType
from asusrouter.tools.identifiers import MacAddress

MAC = MacAddress.from_value("AA:BB:CC:DD:EE:01")
NVRAM = {ARNvramType.LED: "0"}


def _identity() -> MagicMock:
    """Build an identity mock of the test device."""

    identity = MagicMock(spec=ARDeviceIdentity)
    identity.mac = MAC
    return identity


def _get_data(aimesh: Any) -> AsyncMock:
    """Build a data callback returning nvram and the given AiMesh reply."""

    async def get_data(request: Any, **kwargs: Any) -> Any:
        if request is ARAiMeshSourceUniversal:
            return aimesh
        return NVRAM

    return AsyncMock(side_effect=get_data)


class TestGetState:
    """Tests for fetch_state."""

    async def test_fetches_via_nvram(self) -> None:
        """The LED item is requested from the NVRAM module."""

        values = {ARNvramType.LED: "1"}
        get_data = AsyncMock(return_value=values)
        callback = AsyncMock()

        result = await fetch_state(
            callback, ARLedSourceUniversal, fetch_data_callback=get_data
        )

        assert result == values
        callback.assert_not_awaited()
        requested = get_data.await_args.args[0]
        assert set(requested) == {ARNvramType.LED}

    async def test_no_get_data_callback(self) -> None:
        """Without a data callback nothing is fetched."""

        callback = AsyncMock()
        result = await fetch_state(callback, ARLedSourceUniversal)
        assert result == {}
        callback.assert_not_awaited()

    async def test_non_dict_response(self) -> None:
        """A non-dict response is normalized to an empty dict."""

        get_data = AsyncMock(return_value=None)
        result = await fetch_state(
            AsyncMock(), ARLedSourceUniversal, fetch_data_callback=get_data
        )
        assert result == {}


class TestAiMeshState:
    """Tests for the LED state from the AiMesh config."""

    @pytest.mark.parametrize("led", [True, False])
    async def test_aimesh_wins(self, led: bool) -> None:
        """The AiMesh config of the device replaces the nvram state."""

        topology = ARAiMeshTopology(
            nodes={MAC: ARAiMeshNode(mac=MAC, led=led)}
        )
        get_data = _get_data({ARAiMeshSourceUniversal: topology})

        result = await fetch_state(
            AsyncMock(),
            ARLedSourceUniversal,
            fetch_data_callback=get_data,
            identity=_identity(),
        )

        assert result == {ARNvramType.LED: led}
        assert translate_state(result)[ARLedField.STATE] is led
        # The nvram reply is left as fetched
        assert NVRAM == {ARNvramType.LED: "0"}

    @pytest.mark.parametrize(
        "aimesh",
        [
            None,
            {},
            {ARAiMeshSourceUniversal: {}},
            {ARAiMeshSourceUniversal: ARAiMeshTopology()},
            {
                ARAiMeshSourceUniversal: ARAiMeshTopology(
                    nodes={MAC: ARAiMeshNode(mac=MAC)}
                )
            },
        ],
        ids=["none", "empty", "not_topology", "no_node", "no_led"],
    )
    async def test_nvram_fallback(self, aimesh: Any) -> None:
        """Without an AiMesh LED state the nvram one is kept."""

        result = await fetch_state(
            AsyncMock(),
            ARLedSourceUniversal,
            fetch_data_callback=_get_data(aimesh),
            identity=_identity(),
        )

        assert result == NVRAM

    async def test_no_identity(self) -> None:
        """Without an identity AiMesh is not read."""

        get_data = _get_data(None)

        result = await fetch_state(
            AsyncMock(), ARLedSourceUniversal, fetch_data_callback=get_data
        )

        assert result == NVRAM
        get_data.assert_awaited_once()


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
