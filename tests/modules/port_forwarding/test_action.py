"""Tests for the port forwarding action."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock

import pytest

from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.port_forwarding.action import (
    ARPortForwardingAction,
    _spec_matches,
    run_action,
)
from asusrouter.modules.port_forwarding.enums import (
    ARPortForwardingCommand,
    ARPortForwardingField,
    ARPortForwardingProtocol,
)
from asusrouter.modules.port_forwarding.source import (
    ARPortForwardingSourceUniversal,
    serialize_rules,
)
from asusrouter.tools.identifiers.ip import IpAddress

_F = ARPortForwardingField
_P = ARPortForwardingProtocol

RULE_A: dict[ARPortForwardingField, Any] = {
    _F.NAME: "A",
    _F.PROTOCOL: _P.TCP,
    _F.EXTERNAL_PORT: "80",
    _F.INTERNAL_IP: "192.168.1.10",
}
RULE_B: dict[ARPortForwardingField, Any] = {
    _F.NAME: "B",
    _F.PROTOCOL: _P.UDP,
    _F.EXTERNAL_PORT: "53",
    _F.INTERNAL_IP: "192.168.1.11",
}
RULE_OTHER: dict[ARPortForwardingField, Any] = {
    _F.NAME: "G",
    _F.PROTOCOL: _P.OTHER,
    _F.PROTOCOL_NUMBER: 47,
    _F.INTERNAL_IP: "192.168.1.12",
}
RULE_SECONDARY: dict[ARPortForwardingField, Any] = {
    _F.NAME: "S",
    _F.PROTOCOL: _P.TCP,
    _F.EXTERNAL_PORT: "22",
    _F.INTERNAL_IP: "192.168.1.13",
    _F.WAN_UNIT: 1,
}
RULE_C: dict[ARPortForwardingField, Any] = {
    _F.NAME: "C",
    _F.PROTOCOL: _P.TCP,
    _F.EXTERNAL_PORT: "81",
    _F.INTERNAL_IP: "192.168.1.14",
}
RULE_SRC: dict[ARPortForwardingField, Any] = {
    _F.NAME: "D",
    _F.PROTOCOL: _P.UDP,
    _F.EXTERNAL_PORT: "443",
    _F.INTERNAL_IP: "192.168.1.15",
    _F.SOURCE_IP: "10.0.0.0/24",
}
# Same device key as RULE_A (unit 0, TCP, port 80, no source) but a
# different name and internal IP - a duplicate as far as the device cares
RULE_A_DUP: dict[ARPortForwardingField, Any] = {
    _F.NAME: "A-again",
    _F.PROTOCOL: _P.TCP,
    _F.EXTERNAL_PORT: "80",
    _F.INTERNAL_IP: "192.168.1.99",
}
# RULE_A restricted to a source - a distinct rule, not a duplicate
RULE_A_SRC: dict[ARPortForwardingField, Any] = {
    _F.NAME: "A-src",
    _F.PROTOCOL: _P.TCP,
    _F.EXTERNAL_PORT: "80",
    _F.INTERNAL_IP: "192.168.1.10",
    _F.SOURCE_IP: "10.0.0.0/24",
}


def _poster() -> AsyncMock:
    """Build a push callback that reports the firewall restart ran."""

    return AsyncMock(return_value={"run_service": "restart_firewall"})


def _data(rules: list[dict[ARPortForwardingField, Any]] | None) -> AsyncMock:
    """Build a get-data callback for the given current rules."""

    payload = None if rules is None else {_F.RULES: rules}
    return AsyncMock(return_value={ARPortForwardingSourceUniversal: payload})


def _payload(callback: AsyncMock) -> dict[str, Any]:
    """Decode the pushed request body."""

    request = callback.await_args.kwargs["request"]
    assert callback.await_args.kwargs["endpoint"] is AREndpoint.PUSH_DATA
    return json.loads(request)


class TestState:
    """Master toggle command."""

    @pytest.mark.parametrize(("state", "expected"), [(True, 1), (False, 0)])
    async def test_toggle(self, state: bool, expected: int) -> None:
        """A STATE command sets vts_enable_x and restarts the firewall."""

        callback = _poster()
        action = ARPortForwardingAction(
            command=ARPortForwardingCommand.STATE, state=state
        )
        result = await run_action(callback, action)

        payload = _payload(callback)
        assert payload["rc_service"] == "restart_firewall"
        assert payload["vts_enable_x"] == expected
        assert result.success is True

    async def test_missing_state(self) -> None:
        """A STATE command without a state does nothing."""

        callback = _poster()
        action = ARPortForwardingAction(command=ARPortForwardingCommand.STATE)
        result = await run_action(callback, action)

        assert result.success is False
        callback.assert_not_awaited()


class TestRules:
    """Rule mutation commands."""

    async def test_unknown_command(self) -> None:
        """An unknown command is rejected without a push."""

        callback = _poster()
        action = ARPortForwardingAction(
            command=ARPortForwardingCommand.UNKNOWN
        )
        result = await run_action(callback, action)

        assert result.success is False
        callback.assert_not_awaited()

    async def test_add(self) -> None:
        """ADD appends to the fetched rules."""

        callback = _poster()
        action = ARPortForwardingAction(
            command=ARPortForwardingCommand.ADD, rules=[RULE_B]
        )
        result = await run_action(
            callback, action, get_data_callback=_data([RULE_A])
        )

        assert _payload(callback)["vts_rulelist"] == serialize_rules(
            [RULE_A, RULE_B]
        )
        assert result.success is True

    async def test_add_without_data_callback(self) -> None:
        """ADD needs the current rules; missing callback fails."""

        callback = _poster()
        action = ARPortForwardingAction(
            command=ARPortForwardingCommand.ADD, rules=[RULE_A]
        )
        result = await run_action(callback, action)

        assert result.success is False
        callback.assert_not_awaited()

    async def test_add_bad_fetch(self) -> None:
        """A non-dict fetch result fails the action."""

        callback = _poster()
        action = ARPortForwardingAction(
            command=ARPortForwardingCommand.ADD, rules=[RULE_A]
        )
        result = await run_action(
            callback, action, get_data_callback=AsyncMock(return_value="x")
        )

        assert result.success is False
        callback.assert_not_awaited()

    async def test_add_none_data(self) -> None:
        """A None source payload is treated as no current rules."""

        callback = _poster()
        action = ARPortForwardingAction(
            command=ARPortForwardingCommand.ADD, rules=[RULE_A]
        )
        result = await run_action(
            callback, action, get_data_callback=_data(None)
        )

        assert _payload(callback)["vts_rulelist"] == serialize_rules([RULE_A])
        assert result.success is True

    async def test_add_empty_noop(self) -> None:
        """ADD with no rules and no current state is a no-op."""

        callback = _poster()
        action = ARPortForwardingAction(command=ARPortForwardingCommand.ADD)
        result = await run_action(
            callback, action, get_data_callback=_data([])
        )

        assert result.success is False
        callback.assert_not_awaited()

    async def test_add_incomplete_rejected(self) -> None:
        """ADD refuses an IP-only rule the device would reject."""

        callback = _poster()
        data = _data([])
        action = ARPortForwardingAction(
            command=ARPortForwardingCommand.ADD,
            rules=[{ARPortForwardingField.INTERNAL_IP: "192.168.1.10"}],
        )
        result = await run_action(callback, action, get_data_callback=data)

        assert result.success is False
        callback.assert_not_awaited()
        data.assert_not_awaited()

    async def test_add_other_missing_number_rejected(self) -> None:
        """ADD refuses an OTHER rule without a protocol number."""

        callback = _poster()
        action = ARPortForwardingAction(
            command=ARPortForwardingCommand.ADD,
            rules=[{_F.PROTOCOL: _P.OTHER, _F.INTERNAL_IP: "192.168.1.10"}],
        )
        result = await run_action(
            callback, action, get_data_callback=_data([])
        )

        assert result.success is False
        callback.assert_not_awaited()

    async def test_add_missing_ip_rejected(self) -> None:
        """ADD refuses a rule without an internal IP."""

        callback = _poster()
        action = ARPortForwardingAction(
            command=ARPortForwardingCommand.ADD,
            rules=[{_F.PROTOCOL: _P.TCP, _F.EXTERNAL_PORT: "80"}],
        )
        result = await run_action(
            callback, action, get_data_callback=_data([])
        )

        assert result.success is False
        callback.assert_not_awaited()

    async def test_remove_bad_fetch(self) -> None:
        """REMOVE fails when the current rules cannot be fetched."""

        callback = _poster()
        action = ARPortForwardingAction(
            command=ARPortForwardingCommand.REMOVE,
            rules=[{_F.INTERNAL_IP: "192.168.1.10"}],
        )
        result = await run_action(
            callback, action, get_data_callback=AsyncMock(return_value="x")
        )

        assert result.success is False
        callback.assert_not_awaited()

    async def test_set_incomplete_rejected(self) -> None:
        """SET refuses a list holding an incomplete rule."""

        callback = _poster()
        action = ARPortForwardingAction(
            command=ARPortForwardingCommand.SET,
            rules=[
                RULE_A,
                {ARPortForwardingField.INTERNAL_IP: "192.168.1.10"},
            ],
        )
        result = await run_action(callback, action)

        assert result.success is False
        callback.assert_not_awaited()

    async def test_set_other_complete(self) -> None:
        """SET accepts a complete OTHER rule."""

        callback = _poster()
        action = ARPortForwardingAction(
            command=ARPortForwardingCommand.SET, rules=[RULE_OTHER]
        )
        result = await run_action(callback, action)

        assert _payload(callback)["vts_rulelist"] == serialize_rules(
            [RULE_OTHER]
        )
        assert result.success is True

    async def test_add_duplicate_of_saved_skipped(self) -> None:
        """ADD of a rule already saved does not create a second copy."""

        callback = _poster()
        action = ARPortForwardingAction(
            command=ARPortForwardingCommand.ADD, rules=[RULE_A_DUP]
        )
        await run_action(callback, action, get_data_callback=_data([RULE_A]))

        # First occurrence (the saved rule) wins; the duplicate is dropped
        assert _payload(callback)["vts_rulelist"] == serialize_rules([RULE_A])

    async def test_saved_duplicates_cleaned(self) -> None:
        """A rule op collapses stale duplicates already in the saved list."""

        callback = _poster()
        action = ARPortForwardingAction(
            command=ARPortForwardingCommand.ADD, rules=[RULE_B]
        )
        await run_action(
            callback, action, get_data_callback=_data([RULE_A, RULE_A_DUP])
        )

        assert _payload(callback)["vts_rulelist"] == serialize_rules(
            [RULE_A, RULE_B]
        )

    async def test_distinct_source_not_deduped(self) -> None:
        """Same port with a different source restriction is kept."""

        callback = _poster()
        action = ARPortForwardingAction(
            command=ARPortForwardingCommand.SET, rules=[RULE_A, RULE_A_SRC]
        )
        await run_action(callback, action)

        assert _payload(callback)["vts_rulelist"] == serialize_rules(
            [RULE_A, RULE_A_SRC]
        )

    async def test_dedup_other_by_protocol_number(self) -> None:
        """Two OTHER rules with the same protocol number collapse."""

        callback = _poster()
        other_dup = {
            **RULE_OTHER,
            _F.NAME: "G2",
            _F.INTERNAL_IP: "192.168.1.9",
        }
        action = ARPortForwardingAction(
            command=ARPortForwardingCommand.SET, rules=[RULE_OTHER, other_dup]
        )
        await run_action(callback, action)

        assert _payload(callback)["vts_rulelist"] == serialize_rules(
            [RULE_OTHER]
        )

    async def test_remove_exact_read_rule(self) -> None:
        """A full read rule as a spec removes exactly that rule."""

        callback = _poster()
        action = ARPortForwardingAction(
            command=ARPortForwardingCommand.REMOVE, rules=[RULE_A]
        )
        result = await run_action(
            callback, action, get_data_callback=_data([RULE_A, RULE_B])
        )

        assert _payload(callback)["vts_rulelist"] == serialize_rules([RULE_B])
        assert result.success is True

    async def test_remove_wildcard_by_port(self) -> None:
        """A partial spec removes on the fields it sets alone."""

        callback = _poster()
        action = ARPortForwardingAction(
            command=ARPortForwardingCommand.REMOVE,
            rules=[{ARPortForwardingField.EXTERNAL_PORT: "80"}],
        )
        result = await run_action(
            callback, action, get_data_callback=_data([RULE_A, RULE_B])
        )

        assert _payload(callback)["vts_rulelist"] == serialize_rules([RULE_B])
        assert result.success is True

    async def test_remove_wildcard_by_protocol_multi(self) -> None:
        """A protocol-only spec drops every rule of that protocol."""

        callback = _poster()
        action = ARPortForwardingAction(
            command=ARPortForwardingCommand.REMOVE,
            rules=[
                {ARPortForwardingField.PROTOCOL: ARPortForwardingProtocol.TCP}
            ],
        )
        result = await run_action(
            callback, action, get_data_callback=_data([RULE_A, RULE_C, RULE_B])
        )

        assert _payload(callback)["vts_rulelist"] == serialize_rules([RULE_B])
        assert result.success is True

    async def test_remove_wildcard_ip_and_port(self) -> None:
        """A spec with two fields matches only rules meeting both."""

        callback = _poster()
        action = ARPortForwardingAction(
            command=ARPortForwardingCommand.REMOVE,
            rules=[
                {
                    ARPortForwardingField.INTERNAL_IP: "192.168.1.10",
                    ARPortForwardingField.EXTERNAL_PORT: "80",
                }
            ],
        )
        result = await run_action(
            callback, action, get_data_callback=_data([RULE_A, RULE_C])
        )

        assert _payload(callback)["vts_rulelist"] == serialize_rules([RULE_C])
        assert result.success is True

    async def test_remove_wildcard_by_source_ip(self) -> None:
        """A source-IP spec matches through interface normalization."""

        callback = _poster()
        action = ARPortForwardingAction(
            command=ARPortForwardingCommand.REMOVE,
            rules=[{ARPortForwardingField.SOURCE_IP: "10.0.0.0/24"}],
        )
        result = await run_action(
            callback, action, get_data_callback=_data([RULE_SRC, RULE_B])
        )

        assert _payload(callback)["vts_rulelist"] == serialize_rules([RULE_B])
        assert result.success is True

    async def test_remove_no_specs_rejected(self) -> None:
        """REMOVE with only empty specs and no IPs does nothing."""

        callback = _poster()
        action = ARPortForwardingAction(
            command=ARPortForwardingCommand.REMOVE, rules=[{}]
        )
        result = await run_action(
            callback, action, get_data_callback=_data([RULE_A, RULE_B])
        )

        assert result.success is False
        callback.assert_not_awaited()

    async def test_remove_other_by_protocol_number(self) -> None:
        """An OTHER rule is matched by its protocol number."""

        callback = _poster()
        action = ARPortForwardingAction(
            command=ARPortForwardingCommand.REMOVE, rules=[RULE_OTHER]
        )
        result = await run_action(
            callback, action, get_data_callback=_data([RULE_OTHER, RULE_B])
        )

        assert _payload(callback)["vts_rulelist"] == serialize_rules([RULE_B])
        assert result.success is True

    async def test_remove_by_ip(self) -> None:
        """A spec with just an internal IP drops every rule to that IP."""

        callback = _poster()
        action = ARPortForwardingAction(
            command=ARPortForwardingCommand.REMOVE,
            rules=[{_F.INTERNAL_IP: "192.168.1.10"}],
        )
        result = await run_action(
            callback, action, get_data_callback=_data([RULE_A, RULE_B])
        )

        assert _payload(callback)["vts_rulelist"] == serialize_rules([RULE_B])
        assert result.success is True

    async def test_remove_by_ip_accepts_ipaddress(self) -> None:
        """An IpAddress value in a spec matches a rule's typed IP."""

        callback = _poster()
        action = ARPortForwardingAction(
            command=ARPortForwardingCommand.REMOVE,
            rules=[{_F.INTERNAL_IP: IpAddress("192.168.1.10")}],
        )
        result = await run_action(
            callback, action, get_data_callback=_data([RULE_A, RULE_B])
        )

        assert _payload(callback)["vts_rulelist"] == serialize_rules([RULE_B])
        assert result.success is True

    async def test_remove_multiple_specs(self) -> None:
        """REMOVE drops rules matching any of several specs."""

        callback = _poster()
        action = ARPortForwardingAction(
            command=ARPortForwardingCommand.REMOVE,
            rules=[RULE_A, {_F.INTERNAL_IP: "192.168.1.11"}],
        )
        result = await run_action(
            callback, action, get_data_callback=_data([RULE_A, RULE_B])
        )

        assert _payload(callback)["vts_rulelist"] == ""
        assert result.success is True

    async def test_set_replaces(self) -> None:
        """SET replaces the whole primary list."""

        callback = _poster()
        action = ARPortForwardingAction(
            command=ARPortForwardingCommand.SET, rules=[RULE_A]
        )
        result = await run_action(callback, action)

        assert _payload(callback)["vts_rulelist"] == serialize_rules([RULE_A])
        assert result.success is True

    async def test_set_empty_clears_primary(self) -> None:
        """SET with no rules clears the primary list."""

        callback = _poster()
        action = ARPortForwardingAction(command=ARPortForwardingCommand.SET)
        result = await run_action(callback, action)

        assert _payload(callback)["vts_rulelist"] == ""
        assert result.success is True

    async def test_set_secondary_writes_both(self) -> None:
        """A secondary-WAN rule writes both list keys."""

        callback = _poster()
        action = ARPortForwardingAction(
            command=ARPortForwardingCommand.SET, rules=[RULE_SECONDARY]
        )
        await run_action(callback, action)

        payload = _payload(callback)
        assert payload["vts_rulelist"] == ""
        assert payload["vts1_rulelist"] == serialize_rules([RULE_SECONDARY])

    async def test_raw_callback_is_poster(self) -> None:
        """When given, the raw callback posts instead of the reader."""

        callback = _poster()
        raw = _poster()
        action = ARPortForwardingAction(
            command=ARPortForwardingCommand.STATE, state=True
        )
        await run_action(callback, action, raw_callback=raw)

        raw.assert_awaited_once()
        callback.assert_not_awaited()


class TestExpire:
    """Cache invalidation after a successful action."""

    async def test_expire_called_on_success(self) -> None:
        """A successful action expires the cached port forwarding data."""

        callback = _poster()
        expire = AsyncMock()
        action = ARPortForwardingAction(
            command=ARPortForwardingCommand.STATE, state=True
        )
        await run_action(callback, action, expire_callback=expire)

        expire.assert_awaited_once_with(ARPortForwardingSourceUniversal)

    async def test_no_expire_on_failed_push(self) -> None:
        """A failed push leaves the cache untouched."""

        callback = AsyncMock(return_value=None)
        expire = AsyncMock()
        action = ARPortForwardingAction(
            command=ARPortForwardingCommand.STATE, state=True
        )
        result = await run_action(callback, action, expire_callback=expire)

        assert result.success is False
        expire.assert_not_awaited()


def test_spec_matches_empty_never_matches() -> None:
    """An empty spec matches no rule."""

    assert _spec_matches({}, RULE_A) is False
