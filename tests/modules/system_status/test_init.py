"""Tests for the system status module."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from asusrouter.config.connection import (
    ARConnectionConfig,
    ARConnectionConfigKey as ARCCKey,
)
from asusrouter.modules.common.metrics import ARMetricType as M
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.source import ARDataSource
from asusrouter.modules.system_status import (
    ARSystemStatusSource,
    ARSystemStatusSourceUniversal,
    ARSystemType as T,
    fetch_state,
    legacy,
    translate_state,
)
from asusrouter.tools.identifiers import MacAddress

_MAC = "12:34:56:78:9A:BC"
_MEM = {"mem_free": "400", "mem_total": "1000", "mem_used": "600"}
_KIB = 1024


def _force_config() -> ARConnectionConfig:
    """Build a connection config forcing the legacy data path."""

    config = ARConnectionConfig()
    config.set(ARCCKey.FORCE_LEGACY_SYSTEM_STATUS, True)
    return config


def _legacy_callback(cpu: dict[str, Any], mem: dict[str, Any]) -> AsyncMock:
    """Build a callback returning legacy appGet cpu/ram data."""

    async def call(*, endpoint: AREndpoint, request: str) -> dict[str, Any]:
        return {"cpu_usage": cpu, "memory_usage": mem}

    return AsyncMock(side_effect=call)


def _fallback_callback(cpu: dict[str, Any], mem: dict[str, Any]) -> AsyncMock:
    """Build a callback with an empty modern endpoint and legacy data."""

    async def call(*, endpoint: AREndpoint, request: str) -> dict[str, Any]:
        if endpoint == AREndpoint.FETCH_DATA:
            return {"cpu_usage": cpu, "memory_usage": mem}
        return {}

    return AsyncMock(side_effect=call)


def _identity(mac: str | None = _MAC) -> ARDeviceIdentity:
    """Build an identity with the given MAC."""

    identity = ARDeviceIdentity()
    if mac is not None:
        identity._mac = MacAddress(mac)
    return identity


class TestARSystemStatusSource:
    """Tests for ARSystemStatusSource."""

    def test_is_data_source(self) -> None:
        """ARSystemStatusSource subclasses ARDataSource."""

        assert issubclass(ARSystemStatusSource, ARDataSource)

    def test_universal_targets_router(self) -> None:
        """The universal instance has no explicit target."""

        assert ARSystemStatusSourceUniversal.target is None

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (_MAC, MacAddress(_MAC)),
            (MacAddress(_MAC), MacAddress(_MAC)),
            (None, None),
            ("not-a-mac", None),
        ],
        ids=["str", "macaddress", "none", "invalid"],
    )
    def test_target_coercion(
        self, value: Any, expected: MacAddress | None
    ) -> None:
        """Target coerces any input to MacAddress or None."""

        assert ARSystemStatusSource(value).target == expected

    def test_equal_by_target(self) -> None:
        """Same target (any case) compares equal and hashes equal."""

        a = ARSystemStatusSource(_MAC)
        b = ARSystemStatusSource(_MAC.lower())

        assert a == b
        assert hash(a) == hash(b)
        assert len({a, b}) == 1

    def test_not_equal_on_different_target(self) -> None:
        """Different targets are not equal."""

        assert ARSystemStatusSource(_MAC) != ARSystemStatusSource(
            "AA:BB:CC:DD:EE:FF"
        )

    def test_not_equal_to_other_type(self) -> None:
        """Comparison to a non-source is not equal."""

        assert ARSystemStatusSource(_MAC) != "not-a-source"

    def test_repr(self) -> None:
        """Repr includes the target key field."""

        source = ARSystemStatusSource(_MAC)
        text = repr(source)

        assert text.startswith("<ARSystemStatusSource ")
        assert repr(source.target) in text


class TestGetState:
    """Tests for fetch_state."""

    async def test_uses_identity_mac_without_target(self) -> None:
        """Without a target the request filters on the device MAC."""

        callback = AsyncMock(return_value={"contents": [["5", "26"]]})

        result = await fetch_state(
            callback, ARSystemStatusSourceUniversal, identity=_identity()
        )

        assert result == {_MAC: [["5", "26"]]}
        assert callback.await_args is not None
        call = callback.await_args.kwargs
        assert call["endpoint"] == AREndpoint.FETCH_DIAGNOSTICS_DATA
        assert "filter=node_mac" in call["request"]
        assert "content=cpu_usage" in call["request"]

    async def test_uses_explicit_target(self) -> None:
        """An explicit target overrides the device MAC."""

        node = "AA:BB:CC:DD:EE:FF"
        callback = AsyncMock(return_value={"contents": [["1", "2"]]})

        result = await fetch_state(
            callback, ARSystemStatusSource(node), identity=_identity()
        )

        assert result == {node: [["1", "2"]]}

    async def test_no_mac_returns_empty(self) -> None:
        """No target and no device MAC yields an empty result."""

        callback = AsyncMock(return_value={"contents": [["5", "26"]]})

        result = await fetch_state(
            callback,
            ARSystemStatusSourceUniversal,
            identity=_identity(mac=None),
        )

        assert result == {}
        callback.assert_not_awaited()

    @pytest.mark.parametrize(
        "response",
        [{"contents": []}, {}, "not-a-dict", None],
        ids=["empty_contents", "no_contents", "str", "none"],
    )
    async def test_empty_or_bad_response(self, response: Any) -> None:
        """An empty or non-dict response yields an empty result."""

        callback = AsyncMock(return_value=response)

        result = await fetch_state(
            callback, ARSystemStatusSourceUniversal, identity=_identity()
        )

        assert result == {}


class TestTranslateState:
    """Tests for translate_state."""

    def test_translates_usage(self) -> None:
        """Rows become per-MAC cpu/ram usage keyed by enums."""

        result = translate_state({_MAC: [["5", "26"]]}, identity=_identity())

        node = result[MacAddress(_MAC)]
        assert node[T.CPU][M.USAGE] == 5
        assert node[T.RAM][M.USAGE] == 26
        assert all(isinstance(key, MacAddress) for key in result)

    def test_uses_latest_row(self) -> None:
        """The most recent (last) row is used when several are returned."""

        data = {_MAC: [["1", "20"], ["7", "26"], ["9", "26"]]}

        node = translate_state(data, identity=_identity())[MacAddress(_MAC)]

        assert node[T.CPU][M.USAGE] == 9
        assert node[T.RAM][M.USAGE] == 26

    def test_partial_row_keeps_present(self) -> None:
        """A short row keeps only the columns it has."""

        result = translate_state({_MAC: [["7"]]}, identity=_identity())

        node = result[MacAddress(_MAC)]
        assert node[T.CPU][M.USAGE] == 7
        assert T.RAM not in node

    def test_non_int_values_omitted(self) -> None:
        """Non-integer values are dropped, leaving no entry."""

        result = translate_state({_MAC: [["x", "y"]]}, identity=_identity())

        assert result == {}

    @pytest.mark.parametrize(
        "data",
        [{}, "not-a-dict", None, {_MAC: []}, {"bad-mac": [["1", "2"]]}],
        ids=["empty", "str", "none", "empty_contents", "bad_mac"],
    )
    def test_unusable_input(self, data: Any) -> None:
        """Empty, non-dict, or unkeyable input yields an empty result."""

        assert translate_state(data, identity=_identity()) == {}


class TestSourceStash:
    """Tests for the cpu history stashed on the source."""

    def test_stash_returns_previous(self) -> None:
        """Stashing current counters returns the previous sample."""

        source = ARSystemStatusSource()

        assert source.stash_cpu({1: (1, 1)}) is None
        assert source.stash_cpu({1: (2, 2)}) == {1: (1, 1)}


class TestLegacyGetState:
    """Tests for the legacy cpu/ram data path."""

    async def test_force_legacy_uses_appget(self) -> None:
        """The force flag bypasses the modern endpoint."""

        callback = _legacy_callback(
            {"cpu1_total": "100", "cpu1_usage": "10"}, _MEM
        )

        result = await fetch_state(
            callback,
            ARSystemStatusSource(),
            identity=_identity(),
            connection_config=_force_config(),
        )

        assert callback.await_args is not None
        call = callback.await_args.kwargs
        assert call["endpoint"] == AREndpoint.FETCH_DATA
        assert call["request"] == legacy.LEGACY_REQUEST
        # First sample has no previous counters, so only ram is reported
        node = translate_state(result, identity=_identity())[MacAddress(_MAC)]
        assert T.CPU not in node
        assert node[T.RAM][M.TOTAL] == 1000 * _KIB
        assert node[T.RAM][M.USAGE] == 60.0

    async def test_modern_empty_falls_back_to_legacy(self) -> None:
        """An empty modern response falls back to legacy data."""

        callback = _fallback_callback(
            {"cpu1_total": "100", "cpu1_usage": "10"}, _MEM
        )

        result = await fetch_state(
            callback, ARSystemStatusSource(), identity=_identity()
        )

        node = translate_state(result, identity=_identity())[MacAddress(_MAC)]
        assert node[T.RAM][M.USED] == 600 * _KIB

    async def test_usage_computed_on_second_sample(self) -> None:
        """The cached source lets the second sample derive usage."""

        source = ARSystemStatusSource()
        config = _force_config()

        await fetch_state(
            _legacy_callback(
                {
                    "cpu1_total": "100",
                    "cpu1_usage": "10",
                    "cpu2_total": "100",
                    "cpu2_usage": "20",
                },
                _MEM,
            ),
            source,
            identity=_identity(),
            connection_config=config,
        )
        result = await fetch_state(
            _legacy_callback(
                {
                    "cpu1_total": "200",
                    "cpu1_usage": "60",
                    "cpu2_total": "200",
                    "cpu2_usage": "40",
                },
                _MEM,
            ),
            source,
            identity=_identity(),
            connection_config=config,
        )

        node = translate_state(result, identity=_identity())[MacAddress(_MAC)]
        assert node[T.CPU][M.USAGE] == 35.0
        assert node[T.CORE_1][M.USAGE] == 50.0
        assert node[T.CORE_2][M.USAGE] == 20.0

    async def test_cores_beyond_members_feed_aggregate_only(self) -> None:
        """Cores past the member cap still count toward the aggregate."""

        source = ARSystemStatusSource()
        config = _force_config()
        cores = range(1, 10)

        first = {f"cpu{i}_total": "100" for i in cores}
        first.update({f"cpu{i}_usage": "10" for i in cores})
        second = {f"cpu{i}_total": "200" for i in cores}
        second.update({f"cpu{i}_usage": "60" for i in cores})

        await fetch_state(
            _legacy_callback(first, _MEM),
            source,
            identity=_identity(),
            connection_config=config,
        )
        result = await fetch_state(
            _legacy_callback(second, _MEM),
            source,
            identity=_identity(),
            connection_config=config,
        )

        node = translate_state(result, identity=_identity())[MacAddress(_MAC)]
        assert T.CPU in node
        core_types = [t for t in node if t.value.startswith("core_")]
        assert len(core_types) == 8

    async def test_node_target_skips_legacy(self) -> None:
        """Legacy appGet is not queried for a node target."""

        callback = _legacy_callback(
            {"cpu1_total": "100", "cpu1_usage": "10"}, _MEM
        )

        result = await fetch_state(
            callback,
            ARSystemStatusSource("AA:BB:CC:DD:EE:FF"),
            identity=_identity(),
            connection_config=_force_config(),
        )

        assert result == {}
        callback.assert_not_awaited()

    async def test_non_dict_response(self) -> None:
        """A non-dict legacy response yields an empty result."""

        async def call(*, endpoint: AREndpoint, request: str) -> Any:
            return "not-a-dict"

        result = await fetch_state(
            AsyncMock(side_effect=call),
            ARSystemStatusSource(),
            identity=_identity(),
            connection_config=_force_config(),
        )

        assert result == {}

    async def test_empty_data(self) -> None:
        """Empty cpu and ram data yields an empty result."""

        result = await fetch_state(
            _legacy_callback({}, {}),
            ARSystemStatusSource(),
            identity=_identity(),
            connection_config=_force_config(),
        )

        assert result == {}

    async def test_force_legacy_config_error_uses_modern(self) -> None:
        """A config lookup error leaves the modern endpoint in use."""

        config = Mock()
        config.get.side_effect = KeyError
        callback = AsyncMock(return_value={"contents": [["5", "26"]]})

        result = await fetch_state(
            callback,
            ARSystemStatusSourceUniversal,
            identity=_identity(),
            connection_config=config,
        )

        assert result == {_MAC: [["5", "26"]]}
