"""Tests for the system module."""

from unittest import mock

import pytest

from asusrouter.modules.system import (
    STATE_MAP,
    AsusSystem,
    AsusSystemDeprecated,
    set_state,
)

async_callback = mock.AsyncMock()


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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "deprecated_state, repl_state, repl_ver",
    [
        (AsusSystem.REBUILD_AIMESH, AsusSystem.AIMESH_REBUILD, None),
        (AsusSystem.REBUILD_AIMESH, AsusSystem.AIMESH_REBUILD, "1.0.0"),
    ],
)
async def test_set_state_deprecated(deprecated_state, repl_state, repl_ver):
    """Test set_state with a deprecated state."""

    # Prepare the expected warning message
    message = f"Deprecated state `{deprecated_state.name}` from `AsusSystem` \
enum used. Use `{repl_state.name}` instead"
    if repl_ver is not None:
        message += f". This state will be removed in version {repl_ver}"

    # Prepare the expected arguments for the callback function
    expected_args = STATE_MAP.get(
        repl_state,
        {
            "service": repl_state.value,
            "arguments": {},
            "apply": True,
            "expect_modify": False,
        },
    )

    # Mock the AsusSystemDeprecated enum
    with mock.patch.dict(
        "asusrouter.modules.system.AsusSystemDeprecated",
        {deprecated_state: (repl_state, repl_ver)},
    ):
        # Test set_state with the deprecated state
        with mock.patch("asusrouter.modules.system._LOGGER.warning") as mock_warning:
            await set_state(async_callback, deprecated_state)
        mock_warning.assert_called_once_with(message)
        async_callback.assert_called_once_with(**expected_args)

    # Reset the mock callback function
    async_callback.reset_mock()
