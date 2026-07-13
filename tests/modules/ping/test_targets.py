"""Tests for the ping targets module."""

from __future__ import annotations

from unittest.mock import AsyncMock

from asusrouter.const import AR_CALL_RUN_ACTION
from asusrouter.modules.action import ARActionType
from asusrouter.modules.common.status import MODIFY_KEY
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.nvram import ARNvramType
from asusrouter.modules.ping.targets import (
    ARPingTarget,
    ARPingTargetsAction,
    ARPingTargetsSource,
    ARPingTargetsSourceUniversal,
    get_state,
    run_action,
    translate_state,
)
from asusrouter.modules.ping.targets.action import (
    _add,
    _encode_targets,
    _normalize,
    _remove,
)
from asusrouter.modules.ping.targets.source import _parse_targets
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.identifiers.ip import IpAddress

_RAW = "<Cloudflare>1.1.1.1<Cloudflare>1.0.0.1<Google>8.8.8.8"


def _ip(value: str) -> IpAddress:
    """Build an Ip address from a string."""

    ip = IpAddress.from_value_safe(value)
    assert ip is not None
    return ip


def _target(name: str, ip: str) -> ARPingTarget:
    """Build a ping target."""

    return ARPingTarget(name=name, ip=_ip(ip))


def _list_callback(raw: str | None) -> AsyncMock:
    """Build a get_data_callback returning the given dns_ping_list value."""

    return AsyncMock(return_value={ARNvramType.DNS_PING_LIST: raw})


class TestParseTargets:
    """Tests for _parse_targets."""

    def test_parses_entries(self) -> None:
        """A raw value parses into ordered targets."""

        assert _parse_targets(_RAW) == [
            _target("Cloudflare", "1.1.1.1"),
            _target("Cloudflare", "1.0.0.1"),
            _target("Google", "8.8.8.8"),
        ]

    def test_decodes_html_entities(self) -> None:
        """A value fetched HTML-entity encoded parses correctly."""

        encoded = "&#60Cloudflare&#621.1.1.1&#60Google&#628.8.8.8"
        assert _parse_targets(encoded) == [
            _target("Cloudflare", "1.1.1.1"),
            _target("Google", "8.8.8.8"),
        ]

    def test_empty(self) -> None:
        """An empty value parses to no targets."""

        assert _parse_targets("") == []

    def test_skips_malformed(self) -> None:
        """Entries without a valid IP are skipped."""

        assert _parse_targets("<NoIp><Bad>not-an-ip<Ok>1.1.1.1") == [
            _target("Ok", "1.1.1.1")
        ]


class TestEncodeTargets:
    """Tests for _encode_targets."""

    def test_roundtrip(self) -> None:
        """Encoding parsed targets reproduces the raw value."""

        assert _encode_targets(_parse_targets(_RAW)) == _RAW

    def test_empty(self) -> None:
        """No targets encode to an empty string."""

        assert _encode_targets([]) == ""


class TestNormalize:
    """Tests for _normalize."""

    def test_keeps_target_name_and_ip(self) -> None:
        """An existing target keeps its name and IP."""

        assert _normalize(_target("X", "1.1.1.1")) == _target("X", "1.1.1.1")

    def test_coerces_target_string_ip(self) -> None:
        """A target built with a string IP is coerced to IpAddress."""

        normalized = _normalize(ARPingTarget("X", "1.1.1.1"))  # type: ignore[arg-type]
        assert normalized == _target("X", "1.1.1.1")
        assert isinstance(normalized.ip, IpAddress)

    def test_drops_target_invalid_ip(self) -> None:
        """A target with an invalid IP is dropped."""

        assert _normalize(ARPingTarget("X", "nope")) is None  # type: ignore[arg-type]

    def test_wraps_bare_ip(self) -> None:
        """A bare IP becomes a target with the default name."""

        assert _normalize(_ip("9.9.9.9")) == _target("target", "9.9.9.9")

    def test_wraps_ip_string(self) -> None:
        """A valid IP string is parsed into a target."""

        assert _normalize("9.9.9.9") == _target("target", "9.9.9.9")

    def test_drops_invalid_string(self) -> None:
        """An invalid IP string is dropped."""

        assert _normalize("not-an-ip") is None


class TestAddRemove:
    """Tests for _add and _remove."""

    def test_add_appends_new_ip(self) -> None:
        """Add appends targets whose IP is new."""

        current = [_target("A", "1.1.1.1")]
        new = [_target("B", "8.8.8.8")]

        assert _add(current, new) == [
            _target("A", "1.1.1.1"),
            _target("B", "8.8.8.8"),
        ]

    def test_add_updates_name_on_ip_match(self) -> None:
        """Add updates the name when the IP already exists."""

        current = [_target("A", "1.1.1.1")]
        new = [_target("renamed", "1.1.1.1")]

        assert _add(current, new) == [_target("renamed", "1.1.1.1")]

    def test_add_same_target_unchanged(self) -> None:
        """Adding an identical target leaves the list unchanged."""

        current = [_target("A", "1.1.1.1")]

        assert _add(current, [_target("A", "1.1.1.1")]) == current

    def test_remove_matches_ip_only(self) -> None:
        """Remove drops by IP, ignoring the name."""

        current = [_target("A", "1.1.1.1"), _target("B", "8.8.8.8")]
        drop = [_target("whatever", "1.1.1.1")]

        assert _remove(current, drop) == [_target("B", "8.8.8.8")]

    def test_add_collapses_duplicate_ips(self) -> None:
        """Add collapses pre-existing duplicate IPs (last name wins)."""

        current = [_target("A", "1.1.1.1"), _target("B", "1.1.1.1")]

        assert _add(current, []) == [_target("B", "1.1.1.1")]

    def test_remove_collapses_duplicate_ips(self) -> None:
        """Remove collapses pre-existing duplicate IPs (last name wins)."""

        current = [_target("A", "1.1.1.1"), _target("B", "1.1.1.1")]

        assert _remove(current, [_target("x", "8.8.8.8")]) == [
            _target("B", "1.1.1.1")
        ]


class TestSource:
    """Tests for the targets source."""

    def test_equal_by_type(self) -> None:
        """Sources are equal by exact type."""

        assert ARPingTargetsSource() == ARPingTargetsSourceUniversal

    def test_registered(self) -> None:
        """The source resolves to the module get_state callable."""

        assert (
            ARCallReg.get_callable(ARPingTargetsSourceUniversal, "get_state")
            is get_state
        )


class TestGetState:
    """Tests for get_state."""

    async def test_no_data_callback(self) -> None:
        """Without a data callback nothing is fetched."""

        assert await get_state(AsyncMock(), ARPingTargetsSourceUniversal) is (
            None
        )

    async def test_returns_raw(self) -> None:
        """The raw dns_ping_list value is returned."""

        result = await get_state(
            AsyncMock(),
            ARPingTargetsSourceUniversal,
            get_data_callback=_list_callback(_RAW),
        )
        assert result == _RAW

    async def test_non_dict_values(self) -> None:
        """A non-dict nvram reply yields no data."""

        result = await get_state(
            AsyncMock(),
            ARPingTargetsSourceUniversal,
            get_data_callback=AsyncMock(return_value=None),
        )
        assert result is None


class TestTranslateState:
    """Tests for translate_state."""

    def test_parses_string(self) -> None:
        """A raw string translates into targets."""

        assert translate_state(_RAW) == _parse_targets(_RAW)

    def test_non_string(self) -> None:
        """A non-string yields an empty list."""

        assert translate_state(None) == []


class TestAction:
    """Tests for the targets action."""

    def test_normalizes_targets(self) -> None:
        """Targets, bare IPs and IP strings normalize; invalids drop."""

        action = ARPingTargetsAction(
            ARActionType.ADD,
            [_ip("9.9.9.9"), _target("X", "1.1.1.1"), "8.8.8.8", "nope"],
        )
        assert action.op is ARActionType.ADD
        assert action.targets == [
            _target("target", "9.9.9.9"),
            _target("X", "1.1.1.1"),
            _target("target", "8.8.8.8"),
        ]

    def test_accepts_single_string(self) -> None:
        """A bare IP string is treated as one target, not iterated."""

        action = ARPingTargetsAction(ARActionType.ADD, "192.168.55.21")
        assert action.targets == [_target("target", "192.168.55.21")]

    def test_accepts_single_ip(self) -> None:
        """A bare IP is treated as one target."""

        action = ARPingTargetsAction(ARActionType.ADD, _ip("9.9.9.9"))
        assert action.targets == [_target("target", "9.9.9.9")]

    def test_accepts_single_target(self) -> None:
        """A bare target is treated as one target."""

        target = _target("X", "1.1.1.1")
        assert ARPingTargetsAction(ARActionType.ADD, target).targets == [
            target
        ]

    def test_defaults_to_empty(self) -> None:
        """Without targets the action carries an empty list."""

        assert ARPingTargetsAction(ARActionType.CLEAN).targets == []

    def test_registered(self) -> None:
        """The action resolves to the module run_action callable."""

        assert (
            ARCallReg.get_callable(
                ARPingTargetsAction(ARActionType.CLEAN), AR_CALL_RUN_ACTION
            )
            is run_action
        )


class TestRunAction:
    """Tests for run_action."""

    async def test_clean_skips_fetch(self) -> None:
        """Clean applies an empty list without reading the current one."""

        callback = AsyncMock(return_value={MODIFY_KEY: "1"})
        get_data_callback = _list_callback(_RAW)

        result = await run_action(
            callback,
            ARPingTargetsAction(ARActionType.CLEAN),
            get_data_callback=get_data_callback,
        )

        assert result is True
        get_data_callback.assert_not_awaited()
        call = callback.await_args.kwargs
        assert call["endpoint"] == AREndpoint.PUSH_DATA
        assert "action_mode" in call["request"]

    async def test_add_reads_and_applies(self) -> None:
        """Add fetches the current list, appends, then writes."""

        callback = AsyncMock(return_value={MODIFY_KEY: "1"})
        get_data_callback = _list_callback("<A>1.1.1.1")

        result = await run_action(
            callback,
            ARPingTargetsAction(ARActionType.ADD, [_ip("8.8.8.8")]),
            get_data_callback=get_data_callback,
        )

        assert result is True
        get_data_callback.assert_awaited_once_with(
            ARNvramType.DNS_PING_LIST, force=True
        )
        request = callback.await_args.kwargs["request"]
        assert "1.1.1.1" in request
        assert "8.8.8.8" in request

    async def test_remove_reads_and_applies(self) -> None:
        """Remove fetches the current list and drops by IP."""

        callback = AsyncMock(return_value={MODIFY_KEY: "1"})
        get_data_callback = _list_callback("<A>1.1.1.1<B>8.8.8.8")

        result = await run_action(
            callback,
            ARPingTargetsAction(ARActionType.REMOVE, [_ip("1.1.1.1")]),
            get_data_callback=get_data_callback,
        )

        assert result is True
        request = callback.await_args.kwargs["request"]
        assert "1.1.1.1" not in request
        assert "8.8.8.8" in request

    async def test_add_unchanged_skips_write(self) -> None:
        """Adding an already-present target reads but does not write."""

        callback = AsyncMock()
        get_data_callback = _list_callback("<target>9.9.9.9")

        result = await run_action(
            callback,
            ARPingTargetsAction(ARActionType.ADD, "9.9.9.9"),
            get_data_callback=get_data_callback,
        )

        assert result is True
        get_data_callback.assert_awaited_once()
        callback.assert_not_awaited()

    async def test_remove_absent_skips_write(self) -> None:
        """Removing a target that is not present does not write."""

        callback = AsyncMock()
        get_data_callback = _list_callback("<A>1.1.1.1")

        result = await run_action(
            callback,
            ARPingTargetsAction(ARActionType.REMOVE, "8.8.8.8"),
            get_data_callback=get_data_callback,
        )

        assert result is True
        callback.assert_not_awaited()

    async def test_add_without_targets(self) -> None:
        """Add with no valid target skips both requests."""

        callback = AsyncMock()
        get_data_callback = _list_callback(_RAW)

        result = await run_action(
            callback,
            ARPingTargetsAction(ARActionType.ADD, ["not-an-ip"]),
            get_data_callback=get_data_callback,
        )

        assert result is False
        callback.assert_not_awaited()
        get_data_callback.assert_not_awaited()

    async def test_add_without_data_callback(self) -> None:
        """Add without a data callback fails without writing."""

        callback = AsyncMock()
        result = await run_action(
            callback, ARPingTargetsAction(ARActionType.ADD, [_ip("1.1.1.1")])
        )

        assert result is False
        callback.assert_not_awaited()

    async def test_unknown_op(self) -> None:
        """An unknown operation fails without writing."""

        callback = AsyncMock()
        result = await run_action(
            callback,
            ARPingTargetsAction(ARActionType.UNKNOWN),
            get_data_callback=_list_callback(_RAW),
        )

        assert result is False
        callback.assert_not_awaited()

    async def test_modify_false(self) -> None:
        """A falsy modify flag reports failure."""

        callback = AsyncMock(return_value={MODIFY_KEY: "0"})
        result = await run_action(
            callback,
            ARPingTargetsAction(ARActionType.CLEAN),
        )

        assert result is False

    async def test_non_dict_response(self) -> None:
        """A non-dict applyapp reply reports failure."""

        callback = AsyncMock(return_value=None)
        result = await run_action(
            callback,
            ARPingTargetsAction(ARActionType.CLEAN),
        )

        assert result is False
