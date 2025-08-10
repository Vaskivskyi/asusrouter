"""Tests for the led module."""

from unittest.mock import AsyncMock, MagicMock, patch

from asusrouter.modules.endpoint import Endpoint
from asusrouter.modules.identity import AsusDevice
from asusrouter.modules.led import AsusLED, keep_state, set_state
import pytest


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
        (None, AsusLED.OFF, False, 0),
        (MagicMock(spec=AsusDevice, endpoints={}), AsusLED.OFF, False, 0),
        (
            MagicMock(spec=AsusDevice, endpoints={Endpoint.SYSINFO: None}),
            AsusLED.ON,
            False,
            0,
        ),
        (
            MagicMock(
                spec=AsusDevice, endpoints={Endpoint.SYSINFO: "sysinfo"}
            ),
            AsusLED.OFF,
            True,
            2,
        ),
    ],
)
async def test_keep_state(
    identity: AsusDevice | None,
    state: AsusLED,
    expected: bool,
    set_state_calls: int,
) -> None:
    """Test keep_state."""

    # Arrange
    callback = AsyncMock(return_value=True)
    with patch(
        "asusrouter.modules.led.set_state", new_callable=AsyncMock
    ) as mock_set_state:
        # Act
        result = await keep_state(callback, state, identity=identity)

        # Assert
        assert result is expected
        assert mock_set_state.call_count == set_state_calls
