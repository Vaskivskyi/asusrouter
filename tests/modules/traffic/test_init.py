"""Tests for the traffic supermodule dispatcher."""

from __future__ import annotations

import importlib
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from asusrouter.const import AR_CALL_GET_STATE, AR_CALL_TRANSLATE_STATE
from asusrouter.modules import traffic
from asusrouter.modules.common.metrics import ARMetricType as M
from asusrouter.modules.traffic import get_state, translate_state
from asusrouter.modules.traffic.aimesh import ARTrafficAiMeshSource
from asusrouter.modules.traffic.base import ARTrafficSource, ARTrafficType

_NODE = "AA:BB:CC:00:00:01"
_CONTENT = {ARTrafficType.WIRED: {M.RX_SPEED: 1024.0}}


class TestGetState:
    """Tests for the dispatcher get_state."""

    async def test_without_callback(self) -> None:
        """Without a data callback the dispatcher yields nothing."""

        result = await get_state(
            AsyncMock(), ARTrafficSource(ARTrafficType.WIRED, _NODE)
        )

        assert result == {}

    async def test_delegates_to_aimesh(self) -> None:
        """The dispatcher delegates to AiMesh and returns its content."""

        captured: dict[str, Any] = {}

        async def fake_callback(source: Any) -> dict[Any, Any]:
            captured["source"] = source
            return {source: _CONTENT}

        result = await get_state(
            AsyncMock(),
            ARTrafficSource(ARTrafficType.WIRED, _NODE),
            get_data_callback=fake_callback,
        )

        assert result == _CONTENT
        delegate = captured["source"]
        assert isinstance(delegate, ARTrafficAiMeshSource)
        assert delegate.link == ARTrafficType.WIRED
        assert delegate.target == ARTrafficSource(target=_NODE).target

    async def test_non_dict_results(self) -> None:
        """A non-dict callback result yields an empty state."""

        async def fake_callback(source: Any) -> Any:
            return None

        result = await get_state(
            AsyncMock(),
            ARTrafficSource(target=_NODE),
            get_data_callback=fake_callback,
        )

        assert result == {}

    async def test_non_dict_content(self) -> None:
        """A non-dict content value yields an empty state."""

        async def fake_callback(source: Any) -> dict[Any, Any]:
            return {source: None}

        result = await get_state(
            AsyncMock(),
            ARTrafficSource(target=_NODE),
            get_data_callback=fake_callback,
        )

        assert result == {}


class TestTranslateState:
    """Tests for the dispatcher translate_state."""

    def test_passthrough(self) -> None:
        """A dict is passed through unchanged."""

        assert translate_state(_CONTENT) == _CONTENT

    @pytest.mark.parametrize(
        "data", [None, "x", 5], ids=["none", "str", "int"]
    )
    def test_bad_input(self, data: Any) -> None:
        """A non-dict input yields an empty result."""

        assert translate_state(data) == {}


def test_registers_dispatcher(monkeypatch: pytest.MonkeyPatch) -> None:
    """Importing the supermodule registers the public source."""

    mock_register = Mock()
    monkeypatch.setattr(
        "asusrouter.registry.ARCallableRegistry.register", mock_register
    )

    importlib.reload(traffic)

    mock_register.assert_called_once_with(
        traffic.ARTrafficSource,
        **{
            AR_CALL_GET_STATE: traffic.get_state,
            AR_CALL_TRANSLATE_STATE: traffic.translate_state,
        },
    )
