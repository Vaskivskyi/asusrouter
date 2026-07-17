"""Tests for the wifi action module."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

from asusrouter.const import AR_CALL_RUN_ACTION
from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.service.action import ARServiceResult
from asusrouter.modules.wifi import ARWiFiBand
from asusrouter.modules.wifi.action import ARWiFiAction, run_action
from asusrouter.registry import ARCallableRegistry as ARCallReg

_WIFI = {ARWiFiBand.BAND_2G1: 0, ARWiFiBand.BAND_5G1: 1}


def _identity(wifi: dict[ARWiFiBand, int] | None) -> Any:
    """Build a stub identity carrying a wifi map."""

    return SimpleNamespace(wifi=wifi)


class TestARWiFiAction:
    """Tests for ARWiFiAction."""

    def test_stores_band_and_state(self) -> None:
        """The band and desired state are stored as given."""

        action = ARWiFiAction(ARWiFiBand.BAND_5G1, True)
        assert action.band is ARWiFiBand.BAND_5G1
        assert action.state is True

    def test_equality_and_hash(self) -> None:
        """Actions are equal by band and state."""

        base = ARWiFiAction(ARWiFiBand.BAND_2G1, True)
        assert base == ARWiFiAction(ARWiFiBand.BAND_2G1, True)
        assert hash(base) == hash(ARWiFiAction(ARWiFiBand.BAND_2G1, True))
        assert base != ARWiFiAction(ARWiFiBand.BAND_2G1, False)
        assert base != ARWiFiAction(ARWiFiBand.BAND_5G1, True)
        assert base != object()

    def test_registered(self) -> None:
        """The action resolves a run_action callable via the registry."""

        assert (
            ARCallReg.get_callable(
                ARWiFiAction(ARWiFiBand.BAND_2G1, True), AR_CALL_RUN_ACTION
            )
            is run_action
        )


class TestRunAction:
    """Tests for wifi run_action."""

    async def test_enable_via_raw_callback(self) -> None:
        """Enabling posts wl{unit}_radio=1 to PUSH_DATA via raw callback."""

        fetch_raw_callback = AsyncMock(return_value="NOT MODIFIED")
        callback = AsyncMock()
        action = ARWiFiAction(ARWiFiBand.BAND_5G1, True)

        result = await run_action(
            callback,
            action,
            fetch_raw_callback=fetch_raw_callback,
            identity=_identity(_WIFI),
        )

        assert result.success is True
        callback.assert_not_awaited()
        call = fetch_raw_callback.await_args.kwargs
        assert call["endpoint"] is AREndpoint.PUSH_DATA
        assert '"rc_service":"restart_wireless"' in call["request"]
        assert '"wl1_radio":1' in call["request"]

    async def test_disable_via_callback(self) -> None:
        """With no raw callback, the plain callback posts wl{unit}_radio=0."""

        callback = AsyncMock(return_value={"run_service": "restart_wireless"})
        action = ARWiFiAction(ARWiFiBand.BAND_2G1, False)

        result = await run_action(callback, action, identity=_identity(_WIFI))

        assert result.success is True
        call = callback.await_args.kwargs
        assert call["endpoint"] is AREndpoint.PUSH_DATA
        assert '"wl0_radio":0' in call["request"]

    async def test_band_not_in_wifi(self) -> None:
        """A band absent from the identity map fails without a call."""

        callback = AsyncMock()
        result = await run_action(
            callback,
            ARWiFiAction(ARWiFiBand.BAND_6G1, True),
            identity=_identity(_WIFI),
        )

        assert result == ARServiceResult(success=False)
        callback.assert_not_awaited()

    async def test_no_identity(self) -> None:
        """No identity fails without a call."""

        callback = AsyncMock()
        result = await run_action(
            callback, ARWiFiAction(ARWiFiBand.BAND_2G1, True)
        )

        assert result == ARServiceResult(success=False)
        callback.assert_not_awaited()
