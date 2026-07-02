"""Tests for the support module __init__."""

from __future__ import annotations

import importlib
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from asusrouter.modules.source import ARDataSource
import asusrouter.modules.support as support_mod
from asusrouter.modules.support import (
    ARSupportSource,
    ARSupportSourceUniversal,
    get_state,
    translate_state,
)
from asusrouter.modules.support.flag import ARSupportType


class TestARSupportSource:
    """Tests for ARSupportSource."""

    def test_is_data_source_subclass(self) -> None:
        """ARSupportSource is a subclass of ARDataSource."""

        assert issubclass(ARSupportSource, ARDataSource)

    def test_instantiation(self) -> None:
        """ARSupportSource can be instantiated without arguments."""

        assert isinstance(ARSupportSource(), ARSupportSource)

    def test_universal_instance(self) -> None:
        """ARSupportSourceUniversal is a module-level instance."""

        assert isinstance(ARSupportSourceUniversal, ARSupportSource)


def test_translation_table_covers_all_support_types() -> None:
    """_TRANSLATION_TABLE has an entry for every non-UNKNOWN ARSupportType."""

    for member in ARSupportType:
        if member is ARSupportType.UNKNOWN:
            continue
        assert member in support_mod._TRANSLATION_TABLE


@pytest.mark.asyncio
async def test_get_state_returns_ui_support() -> None:
    """get_state returns the ui_support dict when present."""

    callback = AsyncMock(return_value={"get_ui_support": {"foo": "bar"}})
    result = await get_state(callback, MagicMock())
    assert result == {"foo": "bar"}


@pytest.mark.parametrize(
    "response",
    [
        {},
        None,
        {"get_ui_support": "not_a_dict"},
        {"get_ui_support": None},
    ],
)
@pytest.mark.asyncio
async def test_get_state_returns_empty(response: Any) -> None:
    """get_state returns empty dict when response has no usable ui_support."""

    callback = AsyncMock(return_value=response)
    result = await get_state(callback, MagicMock())
    assert result == {}


def test_translate_state_returns_all_translation_table_keys() -> None:
    """translate_state output has all _TRANSLATION_TABLE keys."""

    result = translate_state({})
    for key in support_mod._TRANSLATION_TABLE:
        assert key in result


def test_module_registers_callables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Module registers callables with ARCallReg on import."""

    mock_register = MagicMock()
    monkeypatch.setattr(
        "asusrouter.registry.ARCallableRegistry.register_module",
        mock_register,
    )
    importlib.reload(support_mod)

    mock_register.assert_called_once()
    args, kwargs = mock_register.call_args
    assert args[0] is support_mod.ARSupportSource
    assert kwargs["get_state"] is support_mod.get_state
    assert kwargs["translate_state"] is support_mod.translate_state
