"""Tests for the system module."""

from unittest.mock import AsyncMock

import pytest

from asusrouter.modules.system import STATE_MAP, AsusSystem, set_state

async_callback = AsyncMock()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "state, expected_args",
    list(STATE_MAP.items())
    + [
        (
            AsusSystem.REBOOT,
            {
                "service": AsusSystem.REBOOT.value,
                "arguments": {},
                "apply": True,
                "expect_modify": False,
            },
        ),
    ],
)
async def test_set_state(state, expected_args):
    """Test set_state."""

    # Test set_state with the given state
    await set_state(async_callback, state)
    async_callback.assert_called_once_with(**expected_args)

    # Reset the mock callback function
    async_callback.reset_mock()
