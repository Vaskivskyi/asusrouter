"""Tests for the wireguard module."""

from unittest.mock import AsyncMock

import pytest

from asusrouter.modules.wireguard import (
    AsusWireGuardClient,
    AsusWireGuardServer,
    _get_arguments,
    set_state,
)


@pytest.mark.parametrize(
    "kwargs, expected",
    [
        # Correct arguments
        ({"arguments": {"id": 1}}, 1),
        ({"id": 2}, 2),
        ({"arguments": {"id": 3}, "id": 4}, 3),
        # Missing arguments
        ({}, 1),
    ],
)
def test_get_arguments(kwargs, expected):
    """Test get_arguments."""

    assert _get_arguments(**kwargs) == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "state, arguments, expect_modify, expected_service, exprected_args, expected_result",
    [
        # Correct states
        (
            AsusWireGuardClient.ON,
            {"id": 1},
            False,
            "start_wgc 1",
            {"id": 1, "wgc_enable": 1, "wgc_unit": 1},
            True,
        ),
        (
            AsusWireGuardClient.OFF,
            {"id": 2},
            True,
            "stop_wgc 2",
            {"id": 2, "wgc_enable": 0, "wgc_unit": 2},
            True,
        ),
        (
            AsusWireGuardServer.ON,
            {"id": 3},
            False,
            "restart_wgs;restart_dnsmasq",
            {"id": 3, "wgs_enable": 1, "wgs_unit": 3},
            True,
        ),
        (
            AsusWireGuardServer.OFF,
            {"id": 4},
            True,
            "restart_wgs;restart_dnsmasq",
            {"id": 4, "wgs_enable": 0, "wgs_unit": 4},
            True,
        ),
        # Wrong states
        (None, {"id": 5}, False, None, None, False),
        (None, None, False, None, None, False),
    ],
)
async def test_set_state(
    state, arguments, expect_modify, expected_service, exprected_args, expected_result
):
    """Test set_state."""

    # Prepare the callback
    callback = AsyncMock(return_value=True)

    # Get the result
    result = await set_state(
        callback, state, arguments=arguments, expect_modify=expect_modify
    )

    # Check the result
    assert result is expected_result

    # Check the callback
    if expected_result:
        callback.assert_called_once_with(
            service=expected_service,
            arguments=exprected_args,
            apply=True,
            expect_modify=expect_modify,
        )
    else:
        callback.assert_not_called()
