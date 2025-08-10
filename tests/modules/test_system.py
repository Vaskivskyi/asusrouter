"""Tests for the system module."""

from typing import Any
from unittest import mock

import pytest

from asusrouter.modules.system import (
    ARGUMENTS_APPEND,
    STATE_MAP,
    AsusSystem,
    set_state,
)


@pytest.mark.parametrize(
    ("state", "expected_args"),
    [
        (AsusSystem.NODE_CONFIG_CHANGE, ["re_mac", "config"]),
        (AsusSystem.NODE_REBOOT, ["device_list"]),
    ],
)
def test_arguments_append(state: AsusSystem, expected_args: list[str]) -> None:
    """Test ARGUMENTS_APPEND dictionary."""

    assert ARGUMENTS_APPEND.get(state) == expected_args


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("state", "extra_args", "should_call"),
    [
        (
            AsusSystem.NODE_CONFIG_CHANGE,
            {"re_mac": "mac", "config": "cfg"},
            True,
        ),
        (AsusSystem.NODE_REBOOT, {"device_list": ["dev1", "dev2"]}, True),
        (AsusSystem.NODE_CONFIG_CHANGE, {"re_mac": "mac"}, False),
        (AsusSystem.NODE_REBOOT, {}, False),
    ],
)
async def test_set_state(
    state: AsusSystem,
    extra_args: dict[str, Any],
    should_call: bool,
) -> None:
    """Test set_state."""

    # Create a mock
    async_callback = mock.AsyncMock()

    # Patch logger to check for error
    with mock.patch("asusrouter.modules.system._LOGGER.error") as mock_error:
        result = await set_state(async_callback, state, **extra_args)
        if should_call:
            async_callback.assert_called_once_with(**STATE_MAP.get(state, {}))
            assert result is not False
            mock_error.assert_not_called()
        else:
            async_callback.assert_not_called()
            assert result is False
            mock_error.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("deprecated_state", "repl_state", "repl_ver"),
    [
        (AsusSystem.REBUILD_AIMESH, AsusSystem.AIMESH_REBUILD, None),
        (AsusSystem.REBUILD_AIMESH, AsusSystem.AIMESH_REBUILD, "1.0.0"),
    ],
)
async def test_set_state_deprecated(
    deprecated_state: AsusSystem,
    repl_state: AsusSystem,
    repl_ver: str | None,
) -> None:
    """Test set_state with a deprecated state."""

    # Create a mock
    async_callback = mock.AsyncMock()

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
        with mock.patch(
            "asusrouter.modules.system._LOGGER.warning"
        ) as mock_warning:
            await set_state(async_callback, deprecated_state)
        mock_warning.assert_called_once_with(message)
        async_callback.assert_called_once_with(**expected_args)
