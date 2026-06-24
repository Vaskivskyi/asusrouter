"""Tests for the ports module source and pipeline."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.ports import (
    ARPortProperty as P,
    ARPortsSource,
    ARPortsSourceUniversal,
    ARPortType,
    get_state,
    translate_state,
)
from asusrouter.modules.source import ARDataSource
from asusrouter.tools.identifiers import MacAddress

_MAC = "12:34:56:78:9A:BC"

_PORT_STATUS = {
    "node_info": {},
    "port_info": {
        _MAC: {
            "W0": {
                "is_on": "1",
                "cap": "1",
                "max_rate": "1000",
                "link_rate": "1000",
            }
        },
    },
}
_ETHERNET = {"portSpeed": {"LAN 1": "G"}}


def _identity(mac: str | None = _MAC) -> ARDeviceIdentity:
    """Build an identity with the given MAC."""

    identity = ARDeviceIdentity()
    if mac is not None:
        identity._mac = MacAddress(mac)
    return identity


class TestARPortsSource:
    """Tests for the ARPortsSource data source."""

    def test_is_data_source(self) -> None:
        """ARPortsSource subclasses ARDataSource."""

        assert issubclass(ARPortsSource, ARDataSource)

    def test_universal_instance(self) -> None:
        """ARPortsSourceUniversal is an ARPortsSource instance."""

        assert isinstance(ARPortsSourceUniversal, ARPortsSource)


class TestGetState:
    """Tests for get_state."""

    @staticmethod
    def _callback(mapping: dict[AREndpoint, Any]) -> AsyncMock:
        """Build a callback returning the mapped value per endpoint."""

        async def side_effect(
            endpoint: AREndpoint, request: str | None = None
        ) -> Any:
            return mapping.get(endpoint, {})

        return AsyncMock(side_effect=side_effect)

    async def test_prefers_port_status(self) -> None:
        """Returns port_status data and does not call the legacy endpoint."""

        callback = self._callback({AREndpoint.FETCH_PORT_STATUS: _PORT_STATUS})

        result = await get_state(
            callback, ARPortsSourceUniversal, identity=_identity()
        )

        assert result == _PORT_STATUS
        callback.assert_awaited_once_with(
            endpoint=AREndpoint.FETCH_PORT_STATUS, request="node_mac=all"
        )

    async def test_falls_back_to_ethernet(self) -> None:
        """Falls back to the legacy endpoint when port_status is empty."""

        callback = self._callback({AREndpoint.FETCH_PORTS_ETHERNET: _ETHERNET})

        result = await get_state(
            callback, ARPortsSourceUniversal, identity=_identity()
        )

        assert result == _ETHERNET
        assert callback.await_count == 2

    async def test_returns_empty_when_nothing_available(self) -> None:
        """Returns {} when neither endpoint yields data."""

        callback = self._callback({})

        result = await get_state(
            callback, ARPortsSourceUniversal, identity=_identity()
        )

        assert result == {}


class TestTranslateState:
    """Tests for translate_state."""

    def test_dispatches_port_status(self) -> None:
        """A port_info payload is translated via the modern parser."""

        result = translate_state(_PORT_STATUS, identity=_identity())

        ports = result[MacAddress(_MAC)].ports
        w0 = next(p for p in ports if p[P.NATIVE_NAME] == "W0")
        assert w0[P.ROLE] == ARPortType.WAN

    def test_dispatches_ethernet(self) -> None:
        """A portSpeed payload is translated via the legacy parser."""

        result = translate_state(_ETHERNET, identity=_identity())

        ports = result[MacAddress(_MAC)].ports
        assert {p[P.NATIVE_NAME] for p in ports} == {"L1"}

    @pytest.mark.parametrize(
        "data",
        [{}, {"unknown": 1}, "not-a-dict", None],
        ids=["empty", "unknown_shape", "str", "none"],
    )
    def test_returns_empty_for_unusable(self, data: Any) -> None:
        """Empty, non-dict, or unrecognized payloads yield {}."""

        assert translate_state(data, identity=_identity()) == {}
