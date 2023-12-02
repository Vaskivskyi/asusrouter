"""Tests for the parental control module."""

from unittest.mock import AsyncMock

import pytest

from asusrouter.modules.parental_control import (
    KEY_PARENTAL_CONTROL_STATE,
    AsusParentalControl,
    set_state,
)

async_callback = AsyncMock()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "state, expect_modify, expect_call, expected_args",
    [
        # Correct states
        (AsusParentalControl.ON, True, True, {KEY_PARENTAL_CONTROL_STATE: 1}),
        (AsusParentalControl.OFF, False, True, {KEY_PARENTAL_CONTROL_STATE: 0}),
        # Wrong states
        (AsusParentalControl.UNKNOWN, False, False, {}),
        (None, False, False, {}),
    ],
)
async def test_set_state(state, expect_modify, expect_call, expected_args):
    """Test set_state."""

    # Call the set_state function
    await set_state(callback=async_callback, state=state, expect_modify=expect_modify)

    # Check if the callback function was called
    if expect_call:
        async_callback.assert_called_once_with(
            service="restart_firewall",
            arguments=expected_args,
            apply=True,
            expect_modify=expect_modify,
        )
    else:
        async_callback.assert_not_called()

    # Reset the mock callback function
    async_callback.reset_mock()
