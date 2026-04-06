"""Tests for the support module base."""

import importlib
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from asusrouter.modules.source import ARDataSource
import asusrouter.modules.support as support_mod
from asusrouter.modules.support import (
    TRANSLATION_TABLE,
    ARSupportSource,
    calls,
    get_state,
    translate_state,
)
from asusrouter.modules.support.flag import ARSupportType


class TestARSupportSource:
    """Tests for ARSupportSource."""

    def test_init(self) -> None:
        """Test initialization of ARSupportSource."""

        with patch.object(
            ARDataSource, "__init__", return_value=None
        ) as mock_init:
            ARSupportSource()
            mock_init.assert_called_once_with()


def test_translation_table() -> None:
    """Test TRANSLATION_TABLE has all ARSupportType keys."""

    for key in [
        ARSupportType.CONNECTIONS,
        ARSupportType.PLATFORM,
        ARSupportType.USB_GENERATION,
        ARSupportType.USB_PORTS,
        ARSupportType.USB_WAN,
        ARSupportType.WIFI_GENERATION,
        ARSupportType.WIFI_MULTIBAND,
        ARSupportType.WIFI_UNITS,
    ]:
        assert key in TRANSLATION_TABLE


@pytest.mark.asyncio
async def test_get_state() -> None:
    """Test get_state returns ui_support dict if present."""

    mock_callback = AsyncMock(return_value={"get_ui_support": {"foo": "bar"}})
    result = await get_state(mock_callback, MagicMock())
    assert result == {"foo": "bar"}


@pytest.mark.parametrize(
    "response",
    [
        ({}),  # Empty dict
        (None),  # Not a dict
    ],
)
@pytest.mark.asyncio
async def test_get_state_returns_empty(response: Any) -> None:
    """Test get_state returns empty dict if no ui_support or fail."""

    mock_callback = AsyncMock(return_value=response)
    result = await get_state(mock_callback, MagicMock())
    assert result == {}


def test_translate_state_calls_all_interpreters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test translate_state calls all interpreters and returns correct keys."""

    fake_data = {"some": "data"}
    for key in TRANSLATION_TABLE:
        monkeypatch.setitem(
            TRANSLATION_TABLE, key, lambda d, k=key: f"called_{k.value}"
        )
    result = translate_state(fake_data)
    for key in TRANSLATION_TABLE:
        assert key.value in result
        assert result[key.value] == f"called_{key.value}"


def test_calls() -> None:
    """Test calls dict is full."""

    assert "get_state" in calls
    assert "translate_state" in calls
    assert callable(calls["get_state"])
    assert callable(calls["translate_state"])


def test_arcallreg_register_called() -> None:
    """Test ARCallReg.register is called with correct arguments."""

    with patch("asusrouter.modules.support.ARCallReg.register") as mock_reg:
        importlib.reload(support_mod)
        mock_reg.assert_called()
