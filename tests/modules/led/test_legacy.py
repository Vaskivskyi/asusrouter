"""Tests for the legacy LED module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.firmware import ARFirmwareType
from asusrouter.modules.led.legacy import AsusLED, keep_state, set_state

_mock_empty = ARDeviceIdentity()

_mock_stock = MagicMock(spec=ARDeviceIdentity)
_mock_stock.firmware.firmware_type = ARFirmwareType.STOCK

_mock_merlin = MagicMock(spec=ARDeviceIdentity)
_mock_merlin.firmware.firmware_type = ARFirmwareType.MERLIN


@pytest.mark.asyncio
async def test_set_state() -> None:
    """Test set_state."""

    # Arrange
    callback = AsyncMock(return_value=True)
    state = AsusLED.ON
    expect_modify = False

    # Act
    result = await set_state(callback, state, expect_modify=expect_modify)

    # Assert
    callback.assert_called_once_with(
        service="start_ctrl_led",
        arguments={"led_val": state.value},
        apply=True,
        expect_modify=expect_modify,
    )
    assert result is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("identity", "state", "expected", "set_state_calls"),
    [
        (_mock_empty, AsusLED.OFF, False, 0),
        (_mock_stock, AsusLED.OFF, False, 0),
        (_mock_merlin, AsusLED.ON, False, 0),
        (_mock_merlin, AsusLED.OFF, True, 2),
    ],
)
async def test_keep_state(
    identity: ARDeviceIdentity,
    state: AsusLED,
    expected: bool,
    set_state_calls: int,
) -> None:
    """Test keep_state."""

    # Arrange
    callback = AsyncMock(return_value=True)
    with patch(
        "asusrouter.modules.led.legacy.set_state", new_callable=AsyncMock
    ) as mock_set_state:
        # Act
        result = await keep_state(callback, state, identity=identity)

        # Assert
        assert result is expected
        assert mock_set_state.call_count == set_state_calls
