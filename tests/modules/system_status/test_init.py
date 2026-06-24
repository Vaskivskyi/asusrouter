"""Tests for the system status module."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.metrics import ARMetricType as M
from asusrouter.modules.source import ARDataSource
from asusrouter.modules.system_status import (
    ARSystemStatusSource,
    ARSystemStatusSourceUniversal,
    ARSystemType as T,
    get_state,
    translate_state,
)
from asusrouter.tools.identifiers import MacAddress

_MAC = "12:34:56:78:9A:BC"


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
        """Repr includes the target."""

        assert "target" in repr(ARSystemStatusSource(_MAC))


class TestGetState:
    """Tests for get_state."""

    async def test_uses_identity_mac_without_target(self) -> None:
        """Without a target the request filters on the device MAC."""

        callback = AsyncMock(return_value={"contents": [["5", "26"]]})

        result = await get_state(
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

        result = await get_state(
            callback, ARSystemStatusSource(node), identity=_identity()
        )

        assert result == {node: [["1", "2"]]}

    async def test_no_mac_returns_empty(self) -> None:
        """No target and no device MAC yields an empty result."""

        callback = AsyncMock(return_value={"contents": [["5", "26"]]})

        result = await get_state(
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

        result = await get_state(
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
