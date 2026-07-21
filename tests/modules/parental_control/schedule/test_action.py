"""Tests for the parental control action."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.parental_control.enums import (
    ARParentalControlCapability,
    ARParentalControlCommand,
    ARParentalControlField,
    ARParentalControlScheduleMode,
    ARParentalControlType,
)
from asusrouter.modules.parental_control.schedule.action import (
    DEFAULT_MAX_ENTRIES,
    DEFAULT_MAX_RULES,
    ARParentalControlAction,
    _max_entries,
    _max_rules,
    _spec_matches,
    run_action,
)
from asusrouter.modules.parental_control.schedule.source import (
    PC_REQUEST,
    ARParentalControlSourceUniversal,
    serialize_rules,
)
from asusrouter.modules.parental_control.schedule.timemap import (
    WEEKDAYS,
    ARScheduleEntry,
)
from asusrouter.modules.support.flag import ARSupportType
from asusrouter.tools.identifiers import MacAddress

_F = ARParentalControlField
_T = ARParentalControlType
_C = ARParentalControlCommand


def _rule(mac: str, name: str, type_: ARParentalControlType) -> dict[Any, Any]:
    """Build a complete rule dict."""

    return {
        _F.MAC: MacAddress.from_value(mac),
        _F.NAME: name,
        _F.TYPE: type_,
        _F.TIMEMAP: "W01E21000700",
    }


RULE_A = _rule("AA:AA:AA:AA:AA:AA", "A", _T.BLOCK)
RULE_B = _rule("BB:BB:BB:BB:BB:BB", "B", _T.TIME)
# Same MAC as RULE_A, different name - a duplicate as far as the device cares
RULE_A_DUP = _rule("AA:AA:AA:AA:AA:AA", "A-again", _T.DISABLE)


def _poster() -> AsyncMock:
    """Build a push callback that reports the firewall restart ran."""

    return AsyncMock(return_value={"run_service": "restart_firewall"})


def _data(rules: list[dict[Any, Any]] | None) -> AsyncMock:
    """Build a get-data callback for the given current rules."""

    payload = None if rules is None else {_F.RULES: rules}
    return AsyncMock(return_value={ARParentalControlSourceUniversal: payload})


def _payload(callback: AsyncMock) -> dict[str, Any]:
    """Decode the pushed request body."""

    request = callback.await_args.kwargs["request"]
    assert callback.await_args.kwargs["endpoint"] is AREndpoint.PUSH_DATA
    return json.loads(request)


class TestState:
    """Rules-engine master toggle."""

    @pytest.mark.parametrize(("state", "expected"), [(True, 1), (False, 0)])
    async def test_toggle(self, state: bool, expected: int) -> None:
        """A STATE command sets MULTIFILTER_ALL and restarts the firewall."""

        callback = _poster()
        action = ARParentalControlAction(command=_C.STATE, state=state)
        result = await run_action(callback, action)

        payload = _payload(callback)
        assert payload["rc_service"] == "restart_firewall"
        assert payload["MULTIFILTER_ALL"] == expected
        assert result.success is True

    async def test_missing_state(self) -> None:
        """A STATE command without a state does nothing."""

        callback = _poster()
        action = ARParentalControlAction(command=_C.STATE)
        result = await run_action(callback, action)

        assert result.success is False
        callback.assert_not_awaited()


class TestRules:
    """Rule mutation commands."""

    async def test_unknown_command(self) -> None:
        """An unknown command is rejected without a push."""

        callback = _poster()
        action = ARParentalControlAction(command=_C.UNKNOWN)
        result = await run_action(callback, action)

        assert result.success is False
        callback.assert_not_awaited()

    async def test_add(self) -> None:
        """ADD prepends the new rule to the fetched rules."""

        callback = _poster()
        action = ARParentalControlAction(command=_C.ADD, rules=[RULE_B])
        result = await run_action(
            callback, action, fetch_data_callback=_data([RULE_A])
        )

        assert _payload(callback)["MULTIFILTER_MAC"] == (
            "BB:BB:BB:BB:BB:BB>AA:AA:AA:AA:AA:AA"
        )
        assert result.success is True

    async def test_add_replaces_existing_mac(self) -> None:
        """An added rule wins over an existing rule for the same MAC."""

        callback = _poster()
        action = ARParentalControlAction(command=_C.ADD, rules=[RULE_A_DUP])
        await run_action(callback, action, fetch_data_callback=_data([RULE_A]))

        payload = _payload(callback)
        assert payload["MULTIFILTER_MAC"] == "AA:AA:AA:AA:AA:AA"
        assert payload["MULTIFILTER_DEVICENAME"] == "A-again"

    async def test_add_without_data_callback(self) -> None:
        """ADD needs the current rules; missing callback fails."""

        callback = _poster()
        action = ARParentalControlAction(command=_C.ADD, rules=[RULE_A])
        result = await run_action(callback, action)

        assert result.success is False
        callback.assert_not_awaited()

    async def test_add_bad_fetch(self) -> None:
        """A non-dict fetch result fails the action."""

        callback = _poster()
        action = ARParentalControlAction(command=_C.ADD, rules=[RULE_A])
        result = await run_action(
            callback, action, fetch_data_callback=AsyncMock(return_value="x")
        )

        assert result.success is False
        callback.assert_not_awaited()

    async def test_add_none_data(self) -> None:
        """A None source payload is treated as no current rules."""

        callback = _poster()
        action = ARParentalControlAction(command=_C.ADD, rules=[RULE_A])
        result = await run_action(
            callback, action, fetch_data_callback=_data(None)
        )

        assert _payload(callback) == serialize_rules([RULE_A]) | {
            "action_mode": "apply",
            "rc_service": "restart_firewall",
        }
        assert result.success is True

    async def test_add_empty_noop(self) -> None:
        """ADD with no rules is a no-op."""

        callback = _poster()
        action = ARParentalControlAction(command=_C.ADD)
        result = await run_action(
            callback, action, fetch_data_callback=_data([])
        )

        assert result.success is False
        callback.assert_not_awaited()

    async def test_add_incomplete_rejected(self) -> None:
        """ADD refuses a rule without a valid MAC or type."""

        callback = _poster()
        data = _data([])
        action = ARParentalControlAction(
            command=_C.ADD, rules=[{_F.NAME: "nope"}]
        )
        result = await run_action(callback, action, fetch_data_callback=data)

        assert result.success is False
        callback.assert_not_awaited()
        data.assert_not_awaited()

    async def test_add_unknown_type_rejected(self) -> None:
        """ADD refuses a rule whose type does not resolve."""

        callback = _poster()
        action = ARParentalControlAction(
            command=_C.ADD,
            rules=[{_F.MAC: MacAddress.from_value("AA:AA:AA:AA:AA:AA")}],
        )
        result = await run_action(
            callback, action, fetch_data_callback=_data([])
        )

        assert result.success is False
        callback.assert_not_awaited()

    async def test_set(self) -> None:
        """SET writes exactly the given rules."""

        callback = _poster()
        action = ARParentalControlAction(
            command=_C.SET, rules=[RULE_A, RULE_B]
        )
        result = await run_action(callback, action)

        assert _payload(callback)["MULTIFILTER_MAC"] == (
            "AA:AA:AA:AA:AA:AA>BB:BB:BB:BB:BB:BB"
        )
        assert result.success is True

    async def test_set_empty_clears(self) -> None:
        """SET with no rules clears the lists."""

        callback = _poster()
        action = ARParentalControlAction(command=_C.SET)
        result = await run_action(callback, action)

        assert _payload(callback)["MULTIFILTER_MAC"] == ""
        assert result.success is True

    async def test_set_incomplete_rejected(self) -> None:
        """SET refuses a list containing an incomplete rule."""

        callback = _poster()
        action = ARParentalControlAction(
            command=_C.SET, rules=[RULE_A, {_F.NAME: "bad"}]
        )
        result = await run_action(callback, action)

        assert result.success is False
        callback.assert_not_awaited()

    async def test_remove(self) -> None:
        """REMOVE drops rules matching a MAC-only spec."""

        callback = _poster()
        action = ARParentalControlAction(
            command=_C.REMOVE,
            rules=[{_F.MAC: MacAddress.from_value("AA:AA:AA:AA:AA:AA")}],
        )
        result = await run_action(
            callback, action, fetch_data_callback=_data([RULE_A, RULE_B])
        )

        assert _payload(callback)["MULTIFILTER_MAC"] == "BB:BB:BB:BB:BB:BB"
        assert result.success is True

    async def test_remove_no_specs(self) -> None:
        """REMOVE with only empty specs fails without fetching."""

        callback = _poster()
        data = _data([RULE_A])
        action = ARParentalControlAction(command=_C.REMOVE, rules=[{}])
        result = await run_action(callback, action, fetch_data_callback=data)

        assert result.success is False
        callback.assert_not_awaited()
        data.assert_not_awaited()

    async def test_remove_without_data_callback(self) -> None:
        """REMOVE needs the current rules; missing callback fails."""

        callback = _poster()
        action = ARParentalControlAction(
            command=_C.REMOVE,
            rules=[{_F.MAC: MacAddress.from_value("AA:AA:AA:AA:AA:AA")}],
        )
        result = await run_action(callback, action)

        assert result.success is False
        callback.assert_not_awaited()


class TestExpire:
    """Cache expiry after a successful action."""

    async def test_expire_on_success(self) -> None:
        """A successful action expires the source and its nvram items."""

        callback = _poster()
        expire = AsyncMock()
        action = ARParentalControlAction(command=_C.STATE, state=True)
        await run_action(callback, action, expire_callback=expire)

        expired = {call.args[0] for call in expire.await_args_list}
        assert ARParentalControlSourceUniversal in expired
        assert set(PC_REQUEST) <= expired

    async def test_no_expire_on_failure(self) -> None:
        """A failed action leaves the cache untouched."""

        callback = AsyncMock(return_value=None)
        expire = AsyncMock()
        action = ARParentalControlAction(command=_C.STATE, state=True)
        await run_action(callback, action, expire_callback=expire)

        expire.assert_not_awaited()


def _identity(max_rules: Any) -> Any:
    """Build a stand-in identity exposing a parental-control rule limit."""

    return SimpleNamespace(
        support={
            ARSupportType.PARENTAL_CONTROL_CAPABILITIES: {
                ARParentalControlCapability.MAX_RULES: max_rules
            }
        }
    )


def _rules(count: int) -> list[dict[Any, Any]]:
    """Build `count` complete rules with distinct MACs."""

    return [
        _rule(f"AA:AA:AA:AA:AA:{index:02X}", f"r{index}", _T.BLOCK)
        for index in range(count)
    ]


class TestMaxRules:
    """The per-device rule limit from identity support."""

    def test_default_without_identity(self) -> None:
        """Absent identity falls back to the firmware default."""

        assert _max_rules(None) == DEFAULT_MAX_RULES

    def test_default_when_unreported(self) -> None:
        """A zero/absent support flag falls back to the default."""

        assert _max_rules(_identity(0)) == DEFAULT_MAX_RULES

    def test_reported_limit(self) -> None:
        """A reported flag overrides the default."""

        assert _max_rules(_identity("32")) == 32

    async def test_set_over_limit_rejected(self) -> None:
        """SET beyond the limit is rejected without a push."""

        callback = _poster()
        action = ARParentalControlAction(command=_C.SET, rules=_rules(3))
        result = await run_action(callback, action, identity=_identity(2))

        assert result.success is False
        callback.assert_not_awaited()

    async def test_set_at_limit_allowed(self) -> None:
        """SET exactly at the limit is applied."""

        callback = _poster()
        action = ARParentalControlAction(command=_C.SET, rules=_rules(2))
        result = await run_action(callback, action, identity=_identity(2))

        assert result.success is True

    async def test_add_over_limit_rejected(self) -> None:
        """ADD that grows the list past the limit is rejected."""

        callback = _poster()
        action = ARParentalControlAction(command=_C.ADD, rules=[RULE_B])
        result = await run_action(
            callback,
            action,
            fetch_data_callback=_data(_rules(2)),
            identity=_identity(2),
        )

        assert result.success is False
        callback.assert_not_awaited()

    async def test_remove_ignores_limit(self) -> None:
        """REMOVE never trips the limit even from an over-limit saved list."""

        callback = _poster()
        action = ARParentalControlAction(
            command=_C.REMOVE, rules=[{_F.NAME: "r0"}]
        )
        result = await run_action(
            callback,
            action,
            fetch_data_callback=_data(_rules(3)),
            identity=_identity(2),
        )

        assert result.success is True


def _entries_identity(max_entries: Any) -> Any:
    """Build a stand-in identity exposing a total schedule-window limit."""

    return SimpleNamespace(
        support={
            ARSupportType.PARENTAL_CONTROL_CAPABILITIES: {
                ARParentalControlCapability.MAX_ENTRIES: max_entries
            }
        }
    )


def _windowed_rule(mac: str, windows: int) -> dict[Any, Any]:
    """Build a TIME rule whose schedule holds `windows` entries."""

    return {
        _F.MAC: MacAddress.from_value(mac),
        _F.NAME: mac,
        _F.TYPE: _T.TIME,
        _F.SCHEDULE: [ARScheduleEntry(days=WEEKDAYS)] * windows,
    }


class TestMaxEntries:
    """The total schedule-window limit from identity support."""

    def test_default_without_identity(self) -> None:
        """Absent identity falls back to the firmware default."""

        assert _max_entries(None) == DEFAULT_MAX_ENTRIES

    def test_reported_limit(self) -> None:
        """A reported flag overrides the default."""

        assert _max_entries(_entries_identity("64")) == 64

    async def test_over_limit_rejected(self) -> None:
        """SET whose windows exceed the total limit is rejected."""

        callback = _poster()
        action = ARParentalControlAction(
            command=_C.SET, rules=[_windowed_rule("AA:AA:AA:AA:AA:AA", 3)]
        )
        result = await run_action(
            callback, action, identity=_entries_identity(2)
        )

        assert result.success is False
        callback.assert_not_awaited()

    async def test_summed_across_rules(self) -> None:
        """Windows are summed over every rule, not counted per rule."""

        callback = _poster()
        action = ARParentalControlAction(
            command=_C.SET,
            rules=[
                _windowed_rule("AA:AA:AA:AA:AA:AA", 2),
                _windowed_rule("BB:BB:BB:BB:BB:BB", 2),
            ],
        )
        result = await run_action(
            callback, action, identity=_entries_identity(3)
        )

        assert result.success is False
        callback.assert_not_awaited()

    async def test_at_limit_allowed(self) -> None:
        """SET exactly at the total window limit is applied."""

        callback = _poster()
        action = ARParentalControlAction(
            command=_C.SET, rules=[_windowed_rule("AA:AA:AA:AA:AA:AA", 2)]
        )
        result = await run_action(
            callback, action, identity=_entries_identity(2)
        )

        assert result.success is True


def _sched_identity(version: Any) -> Any:
    """Build a stand-in identity exposing a `PC_SCHED_V3` version."""

    return SimpleNamespace(
        support={
            ARSupportType.PARENTAL_CONTROL_CAPABILITIES: {
                ARParentalControlCapability.SCHED_VERSION: version
            }
        }
    )


_ONLINE_RULE = {
    _F.MAC: MacAddress.from_value("CC:CC:CC:CC:CC:CC"),
    _F.NAME: "online",
    _F.TYPE: _T.TIME,
    _F.MODE: ARParentalControlScheduleMode.ONLINE,
    _F.TIMEMAP: "M13E17002100",
}


class TestScheduleModeSupport:
    """Gating online-mode rules on `PC_SCHED_V3` support."""

    async def test_online_rejected_without_support(self) -> None:
        """An online rule is refused when the device reports no support."""

        callback = _poster()
        action = ARParentalControlAction(command=_C.SET, rules=[_ONLINE_RULE])
        result = await run_action(callback, action)

        assert result.success is False
        callback.assert_not_awaited()

    async def test_online_rejected_below_min_version(self) -> None:
        """An online rule is refused when the version is below the minimum."""

        callback = _poster()
        action = ARParentalControlAction(command=_C.SET, rules=[_ONLINE_RULE])
        result = await run_action(
            callback, action, identity=_sched_identity(1)
        )

        assert result.success is False
        callback.assert_not_awaited()

    async def test_online_allowed_with_support(self) -> None:
        """An online rule is applied when the device reports support."""

        callback = _poster()
        action = ARParentalControlAction(command=_C.SET, rules=[_ONLINE_RULE])
        result = await run_action(
            callback, action, identity=_sched_identity(3)
        )

        assert _payload(callback)["MULTIFILTER_MACFILTER_DAYTIME_V2"] == (
            "M13E17002100"
        )
        assert result.success is True

    async def test_offline_allowed_without_support(self) -> None:
        """An offline rule needs no support and is always applied."""

        callback = _poster()
        action = ARParentalControlAction(command=_C.SET, rules=[RULE_A])
        result = await run_action(callback, action)

        assert result.success is True


class TestSpecMatches:
    """Direct tests for the removal spec matcher."""

    def test_empty_spec_never_matches(self) -> None:
        """An empty spec must not match any rule."""

        assert _spec_matches({}, RULE_A) is False

    def test_partial_spec_wildcards(self) -> None:
        """A spec matches on only the fields it sets."""

        spec = {_F.TYPE: _T.BLOCK}
        assert _spec_matches(spec, RULE_A) is True
        assert _spec_matches(spec, RULE_B) is False

    def test_plain_field_spec(self) -> None:
        """A spec on a plain field matches by string, absent reads as blank."""

        assert _spec_matches({_F.NAME: "A"}, RULE_A) is True
        assert _spec_matches({_F.NAME: "A"}, {_F.MAC: RULE_A[_F.MAC]}) is False
