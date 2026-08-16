"""Tests for the port forwarding module."""

from unittest.mock import AsyncMock

import pytest

from asusrouter.modules.endpoint.hook import process_port_forwarding
from asusrouter.modules.port_forwarding import (
    KEY_PORT_FORWARDING_LIST,
    KEY_PORT_FORWARDING_STATE,
    AsusPortForwarding,
    PortForwardingRule,
    set_state,
)

async_callback = AsyncMock()


def test_rule_without_external_ip() -> None:
    """A legacy five-field rule has no external IP restriction."""
    result = process_port_forwarding(
        {
            KEY_PORT_FORWARDING_STATE: "1",
            KEY_PORT_FORWARDING_LIST: (
                "&#60Web&#6280&#62192.0.2.10&#628080&#62TCP"
            ),
        }
    )

    [rule] = result["rules"]
    assert rule == PortForwardingRule(
        name="Web",
        ip_address="192.0.2.10",
        port="8080",
        protocol="TCP",
        ip_external=None,
        port_external="80",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("state", "expect_modify", "expect_call", "expected_args"),
    [
        # Correct states
        (AsusPortForwarding.ON, True, True, {KEY_PORT_FORWARDING_STATE: 1}),
        (AsusPortForwarding.OFF, False, True, {KEY_PORT_FORWARDING_STATE: 0}),
        # Wrong states
        (AsusPortForwarding.UNKNOWN, False, False, {}),
        (None, False, False, {}),
    ],
)
async def test_set_state(
    state: AsusPortForwarding | None,
    expect_modify: bool,
    expect_call: bool,
    expected_args: dict[str, int],
) -> None:
    """Test set_state."""

    # Call the set_state function
    await set_state(
        callback=async_callback, state=state, expect_modify=expect_modify
    )

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
