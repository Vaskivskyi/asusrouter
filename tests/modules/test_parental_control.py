"""Tests for the parental control module."""

from unittest import mock
from unittest.mock import AsyncMock

import pytest

from asusrouter.modules.parental_control import (
    KEY_PC_BLOCK_ALL,
    KEY_PC_STATE,
    AsusBlockAll,
    AsusParentalControl,
    ParentalControlRule,
    PCRuleType,
    set_rule,
    set_state,
)

async_callback = AsyncMock()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "state, expect_modify, expect_call, expected_args, expect_call_rule",
    [
        # Correct states
        (AsusParentalControl.ON, True, True, {KEY_PC_STATE: 1}, False),
        (AsusParentalControl.OFF, False, True, {KEY_PC_STATE: 0}, False),
        (AsusBlockAll.ON, True, True, {KEY_PC_BLOCK_ALL: 1}, False),
        (AsusBlockAll.OFF, False, True, {KEY_PC_BLOCK_ALL: 0}, False),
        # ParentalControlRule
        (
            ParentalControlRule(
                mac="00:00:00:00:00:00",
                name="test",
                timemap="",
                type=PCRuleType.BLOCK,
            ),
            False,
            False,
            {},
            True,
        ),
        # Wrong states
        (AsusParentalControl.UNKNOWN, False, False, {}, False),
        (None, False, False, {}, False),
    ],
)
async def test_set_state(
    state, expect_modify, expect_call, expected_args, expect_call_rule
):
    """Test set_state."""

    with mock.patch("asusrouter.modules.parental_control.set_rule") as mock_set_rule:
        # Call the set_state function
        await set_state(
            callback=async_callback, state=state, expect_modify=expect_modify
        )

        # Check if the mock function was called
        if expect_call_rule:
            mock_set_rule.assert_called_once_with(
                async_callback,
                state,
                expect_modify=expect_modify,
            )
        else:
            mock_set_rule.assert_not_called()

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
