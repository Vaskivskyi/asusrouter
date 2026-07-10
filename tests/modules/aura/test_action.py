"""Tests for the Aura action."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from asusrouter.modules.aura.action import (
    ARAuraAction,
    _resolve_scheme,
    run_action,
)
from asusrouter.modules.aura.enums import ARAuraField, ARAuraScheme
from asusrouter.modules.aura.source import ARAuraSourceUniversal
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.support.flag import ARSupportType
from asusrouter.tools.color import Color


def _identity(*, aura: bool = True) -> SimpleNamespace:
    """Build a fake identity exposing an Aura support map."""

    return SimpleNamespace(support={ARSupportType.AURA: aura})


# Default identity for an Aura-capable device
_ID = _identity()


def _fetch(aura: dict[ARAuraField, Any]) -> AsyncMock:
    """Mock get_data_callback returning the source-keyed fetch result."""

    return AsyncMock(return_value={ARAuraSourceUniversal: aura})


def _query(callback: AsyncMock) -> str:
    """Return the request string from the last SET_AURA call."""

    return callback.await_args.kwargs["request"]


class TestResolveScheme:
    """Tests for _resolve_scheme."""

    def test_explicit(self) -> None:
        """An explicit scheme is used directly."""

        action = ARAuraAction(scheme=ARAuraScheme.BREATHING)
        assert _resolve_scheme(action, {}) is ARAuraScheme.BREATHING

    def test_none_uses_current(self) -> None:
        """No scheme falls back to the current one."""

        action = ARAuraAction()
        current = {ARAuraField.SCHEME: ARAuraScheme.MARQUEE}
        assert _resolve_scheme(action, current) is ARAuraScheme.MARQUEE

    def test_on_uses_previous(self) -> None:
        """ON restores the previous scheme."""

        action = ARAuraAction(scheme=ARAuraScheme.ON)
        current = {ARAuraField.SCHEME_PREV: ARAuraScheme.GRADIENT}
        assert _resolve_scheme(action, current) is ARAuraScheme.GRADIENT

    def test_off(self) -> None:
        """OFF stays OFF."""

        action = ARAuraAction(scheme=ARAuraScheme.OFF)
        assert _resolve_scheme(action, {}) is ARAuraScheme.OFF

    def test_unknown_falls_back_to_static(self) -> None:
        """An unresolved scheme falls back to static."""

        action = ARAuraAction()
        current = {ARAuraField.SCHEME: ARAuraScheme.UNKNOWN}
        assert _resolve_scheme(action, current) is ARAuraScheme.STATIC


class TestRunActionScheme:
    """Tests for scheme and night-mode changes."""

    async def test_scheme_only(self) -> None:
        """A scheme change posts just the scheme."""

        callback = AsyncMock(return_value={})
        get_data = _fetch({})
        action = ARAuraAction(scheme=ARAuraScheme.STATIC)

        result = await run_action(
            callback, action, get_data_callback=get_data, identity=_ID
        )

        assert result is True
        assert callback.await_args.kwargs["endpoint"] is AREndpoint.SET_AURA
        assert "ledg_scheme=2" in _query(callback)
        assert "ledg_rgb" not in _query(callback)

    async def test_night_mode_on(self) -> None:
        """night_mode=True switches the device to night."""

        callback = AsyncMock(return_value={})
        get_data = _fetch({ARAuraField.NIGHT_MODE: False})
        action = ARAuraAction(scheme=ARAuraScheme.STATIC, night_mode=True)

        await run_action(
            callback, action, get_data_callback=get_data, identity=_ID
        )
        assert "ledg_night_mode=1" in _query(callback)

    async def test_night_mode_off(self) -> None:
        """night_mode=False switches the device back to day."""

        callback = AsyncMock(return_value={})
        get_data = _fetch({ARAuraField.NIGHT_MODE: True})
        action = ARAuraAction(night_mode=False)

        await run_action(
            callback, action, get_data_callback=get_data, identity=_ID
        )
        assert "ledg_night_mode=0" in _query(callback)

    async def test_night_mode_left_unchanged(self) -> None:
        """No night_mode means the switch is not touched."""

        callback = AsyncMock(return_value={})
        get_data = _fetch({ARAuraField.NIGHT_MODE: True})
        action = ARAuraAction(scheme=ARAuraScheme.STATIC)

        await run_action(
            callback, action, get_data_callback=get_data, identity=_ID
        )
        assert "ledg_night_mode" not in _query(callback)

    async def test_night_mode_ignored_when_unsupported(self) -> None:
        """night_mode is not sent when the device lacks night support."""

        callback = AsyncMock(return_value={})
        get_data = _fetch({})  # no NIGHT_MODE field
        action = ARAuraAction(scheme=ARAuraScheme.STATIC, night_mode=True)

        result = await run_action(
            callback, action, get_data_callback=get_data, identity=_ID
        )
        assert result is True
        assert "ledg_night_mode" not in _query(callback)

    async def test_no_get_data_callback(self) -> None:
        """Missing the data callback still resolves to a default scheme."""

        callback = AsyncMock(return_value={})
        action = ARAuraAction()

        await run_action(callback, action, identity=_ID)
        assert "ledg_scheme=2" in _query(callback)  # static default

    async def test_failure_when_raw_none(self) -> None:
        """A None from the raw poster (404/unavailable) is a failure."""

        callback = AsyncMock(return_value={})
        raw = AsyncMock(return_value=None)
        action = ARAuraAction(scheme=ARAuraScheme.STATIC)
        assert (
            await run_action(callback, action, raw_callback=raw, identity=_ID)
            is False
        )

    async def test_success_on_empty_body(self) -> None:
        """An empty 200 body from the raw poster still means success."""

        callback = AsyncMock(return_value={})
        raw = AsyncMock(return_value="")
        action = ARAuraAction(scheme=ARAuraScheme.STATIC)
        assert (
            await run_action(callback, action, raw_callback=raw, identity=_ID)
            is True
        )
        assert "ledg_scheme=2" in raw.await_args.kwargs["request"]


class TestRunActionColor:
    """Tests for color changes."""

    async def test_color_on_color_scheme(self) -> None:
        """A color on a color scheme builds the ledg_rgb payload."""

        callback = AsyncMock(return_value={})
        current = {
            ARAuraField.SCHEME: ARAuraScheme.STATIC,
            ARAuraField.ZONES: 1,
            ARAuraField.COLORS: {ARAuraScheme.STATIC: [Color(0, 0, 0, 100)]},
        }
        get_data = _fetch(current)
        action = ARAuraAction(color=Color(255, 0, 0))

        await run_action(
            callback, action, get_data_callback=get_data, identity=_ID
        )
        assert "ledg_rgb=" in _query(callback)

    async def test_color_skipped_without_zones(self) -> None:
        """Zero zones sends no ledg_rgb (avoids wiping stored colors)."""

        callback = AsyncMock(return_value={})
        current = {
            ARAuraField.SCHEME: ARAuraScheme.STATIC,
            ARAuraField.ZONES: 0,
        }
        get_data = _fetch(current)
        action = ARAuraAction(color=Color(255, 0, 0))

        await run_action(
            callback, action, get_data_callback=get_data, identity=_ID
        )
        query = _query(callback)
        assert "ledg_scheme=2" in query
        assert "ledg_rgb" not in query

    async def test_color_ignored_on_non_color_scheme(self) -> None:
        """A color on a non-color scheme is ignored."""

        callback = AsyncMock(return_value={})
        get_data = _fetch({ARAuraField.SCHEME: ARAuraScheme.RAINBOW})
        action = ARAuraAction(color=Color(255, 0, 0))

        await run_action(
            callback, action, get_data_callback=get_data, identity=_ID
        )
        assert "ledg_rgb" not in _query(callback)

    async def test_night_colors_never_written(self) -> None:
        """Color edits never write the firmware-dead night colors."""

        callback = AsyncMock(return_value={})
        current = {
            ARAuraField.SCHEME: ARAuraScheme.STATIC,
            ARAuraField.ZONES: 1,
            ARAuraField.NIGHT_MODE: True,
            ARAuraField.COLORS: {ARAuraScheme.STATIC: [Color(0, 0, 0, 100)]},
        }
        get_data = _fetch(current)
        action = ARAuraAction(color=Color(0, 0, 255))

        await run_action(
            callback, action, get_data_callback=get_data, identity=_ID
        )
        query = _query(callback)
        assert "ledg_rgb=" in query
        assert "ledg_night_rgb" not in query


class TestRunActionUnsupported:
    """Tests for a device that does not expose Aura at all."""

    @pytest.mark.parametrize(
        "identity", [None, _identity(aura=False)], ids=["none", "no-aura"]
    )
    async def test_action_ignored(self, identity: object) -> None:
        """No request is made when the device lacks Aura support."""

        callback = AsyncMock()
        raw = AsyncMock()
        get_data = AsyncMock()
        action = ARAuraAction(scheme=ARAuraScheme.STATIC)

        result = await run_action(
            callback,
            action,
            get_data_callback=get_data,
            raw_callback=raw,
            identity=identity,
        )

        assert result is False
        callback.assert_not_awaited()
        raw.assert_not_awaited()
        get_data.assert_not_awaited()


@pytest.mark.parametrize(
    ("kwargs", "attr", "expected"),
    [
        ({"scheme": ARAuraScheme.WAVE}, "scheme", ARAuraScheme.WAVE),
        ({"brightness": 50}, "brightness", 50),
        ({"zone": 2}, "zone", 2),
    ],
)
def test_action_fields(
    kwargs: dict[str, Any], attr: str, expected: Any
) -> None:
    """The action stores its keyword arguments."""

    action = ARAuraAction(**kwargs)
    assert getattr(action, attr) == expected
