"""Tests for the LED action."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.firmware import ARFirmwareType
from asusrouter.modules.led import action as action_module
from asusrouter.modules.led.action import (
    ARLedAction,
    async_recover_state,
    run_action,
)
from asusrouter.modules.led.enums import ARLedField
from asusrouter.modules.led.source import ARLedSourceUniversal
from asusrouter.modules.nvram import ARNvramType


def _identity(firmware_type: ARFirmwareType) -> MagicMock:
    """Build an identity mock reporting the given firmware type."""

    identity = MagicMock(spec=ARDeviceIdentity)
    identity.firmware.firmware_type = firmware_type
    return identity


@pytest.fixture(autouse=True)
def _fast_poll(monkeypatch: pytest.MonkeyPatch) -> None:
    """Poll without sleeping."""

    monkeypatch.setattr(action_module, "_POLL_INTERVAL", 0)


def _poster(service: str = "start_ctrl_led") -> AsyncMock:
    """Build a push callback that reports the given service ran."""

    return AsyncMock(return_value={"run_service": service})


def _data(*states: Any) -> AsyncMock:
    """Build a forcing get-data callback serving the given LED states."""

    responses = [{ARLedSourceUniversal: {ARLedField.STATE: s}} for s in states]
    return AsyncMock(side_effect=responses)


def _payload(callback: AsyncMock) -> dict[str, Any]:
    """Decode the pushed request body."""

    request = callback.await_args.kwargs["request"]
    assert callback.await_args.kwargs["endpoint"] is AREndpoint.PUSH_DATA
    return json.loads(request)


class TestRunAction:
    """Tests for run_action."""

    @pytest.mark.parametrize(("state", "expected"), [(True, 1), (False, 0)])
    async def test_sets_state(self, state: bool, expected: int) -> None:
        """The action controls the LED via start_ctrl_led."""

        callback = _poster()
        result = await run_action(callback, ARLedAction(state=state))

        assert result.success is True
        payload = _payload(callback)
        assert payload["action_mode"] == "apply"
        assert payload["rc_service"] == "start_ctrl_led"
        assert payload[ARNvramType.LED.value] == expected

    async def test_waits_for_settle(self) -> None:
        """The run polls the state until led_val settles, and skips expiry."""

        callback = _poster()
        # Blank first (daemon restarting), then a real value
        get_data = _data(None, True)
        expire = AsyncMock()
        result = await run_action(
            callback,
            ARLedAction(state=True),
            get_data_callback=get_data,
            expire_callback=expire,
        )

        assert result.success is True
        assert get_data.await_count == 2
        get_data.assert_awaited_with(ARLedSourceUniversal)
        expire.assert_not_awaited()

    async def test_settle_ignores_non_dict_poll(self) -> None:
        """A non-dict poll result is treated as not-yet-settled."""

        callback = _poster()
        get_data = AsyncMock(
            side_effect=[
                None,
                {ARLedSourceUniversal: {ARLedField.STATE: True}},
            ]
        )
        result = await run_action(
            callback, ARLedAction(state=True), get_data_callback=get_data
        )

        assert result.success is True
        assert get_data.await_count == 2

    async def test_settle_timeout_still_succeeds(self) -> None:
        """A state that never settles logs but keeps the run successful."""

        callback = _poster()
        get_data = AsyncMock(
            return_value={ARLedSourceUniversal: {ARLedField.STATE: None}}
        )
        result = await run_action(
            callback, ARLedAction(state=True), get_data_callback=get_data
        )

        assert result.success is True
        assert get_data.await_count == action_module._POLL_ATTEMPTS

    async def test_expires_without_data_callback(self) -> None:
        """Without a data callback, a success expires source and nvram item."""

        callback = _poster()
        expire = AsyncMock()
        result = await run_action(
            callback, ARLedAction(state=True), expire_callback=expire
        )

        assert result.success is True
        expired = {call.args[0] for call in expire.await_args_list}
        assert ARLedSourceUniversal in expired
        assert ARNvramType.LED in expired

    async def test_no_effect_on_failure(self) -> None:
        """A failed run neither polls nor expires."""

        callback = _poster("other")
        get_data = _data(True)
        expire = AsyncMock()
        result = await run_action(
            callback,
            ARLedAction(state=True),
            get_data_callback=get_data,
            expire_callback=expire,
        )

        assert result.success is False
        get_data.assert_not_awaited()
        expire.assert_not_awaited()


class TestRecoverState:
    """Post-reboot LED recovery."""

    async def test_merlin_off_toggles(self) -> None:
        """On Merlin with a desired off-state, recovery toggles on then off."""

        run_action = AsyncMock()
        identity = _identity(ARFirmwareType.MERLIN)

        recovered = await async_recover_state(
            run_action, False, identity=identity
        )

        assert recovered is True
        states = [call.args[0].state for call in run_action.await_args_list]
        assert states == [True, False]

    @pytest.mark.parametrize(
        ("desired", "firmware"),
        [
            (False, ARFirmwareType.STOCK),  # not Merlin: boot keeps the state
            (True, ARFirmwareType.MERLIN),  # on-state survives a reboot
            (None, ARFirmwareType.MERLIN),  # never commanded
        ],
    )
    async def test_no_recovery(
        self, desired: bool | None, firmware: ARFirmwareType
    ) -> None:
        """Recovery is a no-op unless a Merlin off-state must be reasserted."""

        run_action = AsyncMock()
        identity = _identity(firmware)

        recovered = await async_recover_state(
            run_action, desired, identity=identity
        )

        assert recovered is False
        run_action.assert_not_awaited()

    async def test_no_identity(self) -> None:
        """Without an identity the firmware cannot be checked, so no-op."""

        run_action = AsyncMock()

        recovered = await async_recover_state(run_action, False, identity=None)

        assert recovered is False
        run_action.assert_not_awaited()


class TestEquality:
    """Actions are equal by their target state."""

    def test_key(self) -> None:
        """Equal state gives equal, same-hash actions."""

        assert ARLedAction(state=True) == ARLedAction(state=True)
        assert ARLedAction(state=True) != ARLedAction(state=False)
        assert hash(ARLedAction(state=True)) == hash(ARLedAction(state=True))
