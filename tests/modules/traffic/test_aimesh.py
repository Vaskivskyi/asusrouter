"""Tests for the AiMesh traffic submodule."""

from __future__ import annotations

import importlib
import logging
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from asusrouter.modules.aimesh.topology import (
    ARAiMeshBackhaul,
    ARAiMeshMedium,
    ARAiMeshNode,
    ARAiMeshRadio,
    ARAiMeshTopology,
)
from asusrouter.modules.common.metrics import ARMetricType as M
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.traffic.aimesh import (
    ARTrafficAiMeshSource,
    get_state,
    source as aimesh,
    translate_state,
)
from asusrouter.modules.traffic.base import ARTrafficType
from asusrouter.modules.wifi import ARWiFiBand
from asusrouter.tools.identifiers import MacAddress

_NODE = "AA:BB:CC:00:00:01"
_PARENT = "AA:BB:CC:00:00:02"
_AP_FH = "AA:BB:CC:11:00:01"
_AP = "AA:BB:CC:11:00:02"
_STA = "AA:BB:CC:22:00:01"

_RAW = {
    "data": {"rx": 1, "tx": 2, "avg_rx": 3, "avg_tx": 4},
    "phy": {"rx": 5, "tx": 6},
    "error_status": 200,
}
_METRICS = {
    M.RX_SPEED: 1024.0,
    M.TX_SPEED: 2048.0,
    M.RX_SPEED_AVG: 3072.0,
    M.TX_SPEED_AVG: 4096.0,
    M.PHY_RX_SPEED: 5 * 2**20,
    M.PHY_TX_SPEED: 6 * 2**20,
}


def _identity(
    *,
    radios: dict[ARWiFiBand, ARAiMeshRadio] | None = None,
    backhaul: ARAiMeshBackhaul | None = None,
    node: bool = True,
) -> ARDeviceIdentity:
    """Build an identity with a single node holding the given parts."""

    identity = ARDeviceIdentity()
    identity._mac = MacAddress(_NODE)
    if node:
        topology = ARAiMeshTopology(
            nodes={
                MacAddress(_NODE): ARAiMeshNode(
                    mac=MacAddress(_NODE),
                    radios=radios or {},
                    backhaul=backhaul,
                )
            }
        )
        identity.update_aimesh(topology)
    return identity


class TestResolve:
    """Tests for endpoint / args resolution from topology."""

    def test_wifi_band_fronthaul(self) -> None:
        """A band resolves to the wifi endpoint with its fronthaul MAC."""

        identity = _identity(
            radios={
                ARWiFiBand.BAND_5G1: ARAiMeshRadio(
                    band=ARWiFiBand.BAND_5G1,
                    mac_fh=MacAddress(_AP_FH),
                    mac_ap=MacAddress(_AP),
                )
            }
        )

        endpoint, args = aimesh._resolve(
            ARWiFiBand.BAND_5G1, MacAddress(_NODE), identity
        )

        assert endpoint == AREndpoint.FETCH_TRAFFIC_WIFI
        assert args == {
            "node_mac": MacAddress(_NODE),
            "band_mac": MacAddress(_AP_FH),
        }

    def test_wifi_band_falls_back_to_ap(self) -> None:
        """With no fronthaul MAC the AP MAC is used."""

        identity = _identity(
            radios={
                ARWiFiBand.BAND_5G1: ARAiMeshRadio(
                    band=ARWiFiBand.BAND_5G1, mac_ap=MacAddress(_AP)
                )
            }
        )

        _, args = aimesh._resolve(
            ARWiFiBand.BAND_5G1, MacAddress(_NODE), identity
        )

        assert args["band_mac"] == MacAddress(_AP)

    @pytest.mark.parametrize(
        ("radios", "node"),
        [
            ({}, True),
            (
                {ARWiFiBand.BAND_5G1: ARAiMeshRadio(band=ARWiFiBand.BAND_5G1)},
                True,
            ),
            (None, False),
        ],
        ids=["missing-band", "no-mac", "no-node"],
    )
    def test_wifi_band_unresolvable(self, radios: Any, node: bool) -> None:
        """An absent radio / MAC / node yields no endpoint."""

        identity = _identity(radios=radios, node=node)

        endpoint, args = aimesh._resolve(
            ARWiFiBand.BAND_5G1, MacAddress(_NODE), identity
        )

        assert endpoint is None
        assert args == {}

    def test_wired_fronthaul(self) -> None:
        """WIRED resolves to the ethernet endpoint as fronthaul."""

        endpoint, args = aimesh._resolve(
            ARTrafficType.WIRED, MacAddress(_NODE), _identity()
        )

        assert endpoint == AREndpoint.FETCH_TRAFFIC_ETHERNET
        assert args == {"node_mac": MacAddress(_NODE), "is_bh": False}

    @pytest.mark.parametrize(
        "medium",
        [ARAiMeshMedium.WIRELESS, ARAiMeshMedium.MLO],
        ids=["wireless", "mlo"],
    )
    def test_backhaul_wireless(self, medium: ARAiMeshMedium) -> None:
        """A wireless backhaul resolves to the station endpoint."""

        identity = _identity(
            backhaul=ARAiMeshBackhaul(
                medium=medium,
                mac_parent=MacAddress(_PARENT),
                mac_sta=MacAddress(_STA),
            )
        )

        endpoint, args = aimesh._resolve(
            ARTrafficType.BACKHAUL, MacAddress(_NODE), identity
        )

        assert endpoint == AREndpoint.FETCH_TRAFFIC_BACKHAUL
        assert args == {
            "node_mac": MacAddress(_PARENT),
            "sta_mac": MacAddress(_STA),
        }

    @pytest.mark.parametrize(
        "medium",
        [ARAiMeshMedium.WIRED, ARAiMeshMedium.PLC, ARAiMeshMedium.MOCA],
        ids=["wired", "plc", "moca"],
    )
    def test_backhaul_wired(self, medium: ARAiMeshMedium) -> None:
        """A wired backhaul resolves to the ethernet endpoint."""

        identity = _identity(
            backhaul=ARAiMeshBackhaul(
                medium=medium, mac_parent=MacAddress(_PARENT)
            )
        )

        endpoint, args = aimesh._resolve(
            ARTrafficType.BACKHAUL, MacAddress(_NODE), identity
        )

        assert endpoint == AREndpoint.FETCH_TRAFFIC_ETHERNET
        assert args == {"node_mac": MacAddress(_NODE), "is_bh": True}

    @pytest.mark.parametrize(
        "backhaul",
        [
            None,
            ARAiMeshBackhaul(medium=ARAiMeshMedium.WIRELESS),
        ],
        ids=["no-backhaul", "incomplete-wireless"],
    )
    def test_backhaul_unresolvable(self, backhaul: Any) -> None:
        """A missing or incomplete backhaul yields no endpoint."""

        identity = _identity(backhaul=backhaul)

        endpoint, args = aimesh._resolve(
            ARTrafficType.BACKHAUL, MacAddress(_NODE), identity
        )

        assert endpoint is None
        assert args == {}

    @pytest.mark.parametrize(
        "link",
        [ARTrafficType.WAN, ARTrafficType.USB, ARTrafficType.LACP],
        ids=["wan", "usb", "lacp"],
    )
    def test_non_aimesh_link(self, link: ARTrafficType) -> None:
        """Non-AiMesh links resolve to no endpoint."""

        endpoint, args = aimesh._resolve(link, MacAddress(_NODE), _identity())

        assert endpoint is None
        assert args == {}


class TestGetState:
    """Tests for get_state."""

    async def test_atomic_calls_endpoint(self) -> None:
        """A specific link fetches one endpoint, keyed by the link."""

        identity = _identity()
        callback = AsyncMock(return_value=_RAW)
        source = ARTrafficAiMeshSource(ARTrafficType.WIRED, _NODE)

        result = await get_state(callback, source, identity=identity)

        assert result == {ARTrafficType.WIRED: _RAW}
        callback.assert_awaited_once()
        kwargs = callback.await_args.kwargs
        assert kwargs["endpoint"] == AREndpoint.FETCH_TRAFFIC_ETHERNET

    async def test_atomic_no_endpoint(self) -> None:
        """An unresolvable link yields an empty result, no fetch."""

        callback = AsyncMock()
        source = ARTrafficAiMeshSource(ARTrafficType.WAN, _NODE)

        result = await get_state(callback, source, identity=_identity())

        assert result == {}
        callback.assert_not_awaited()

    async def test_no_target_no_mac(self) -> None:
        """With no target and no identity MAC nothing is fetched."""

        identity = ARDeviceIdentity()
        callback = AsyncMock()

        result = await get_state(
            callback,
            ARTrafficAiMeshSource(ARTrafficType.WIRED),
            identity=identity,
        )

        assert result == {}
        callback.assert_not_awaited()

    async def test_target_defaults_to_identity_mac(self) -> None:
        """A source without a target uses the connected router MAC."""

        callback = AsyncMock(return_value=_RAW)
        source = ARTrafficAiMeshSource(ARTrafficType.WIRED)

        await get_state(callback, source, identity=_identity())

        args = callback.await_args.kwargs["request"]
        assert args is not None

    async def test_aggregate_fans_out_and_merges(self) -> None:
        """A None link enumerates topology links and merges results."""

        identity = _identity(
            radios={
                ARWiFiBand.BAND_5G1: ARAiMeshRadio(
                    band=ARWiFiBand.BAND_5G1, mac_ap=MacAddress(_AP)
                )
            },
            backhaul=ARAiMeshBackhaul(
                medium=ARAiMeshMedium.WIRED, mac_parent=MacAddress(_PARENT)
            ),
        )

        async def fake_callback(sources: Any) -> dict[Any, Any]:
            return {src: {src.link: _METRICS} for src in sources}

        source = ARTrafficAiMeshSource(target=_NODE)
        result = await get_state(
            AsyncMock(),
            source,
            identity=identity,
            get_data_callback=fake_callback,
        )

        assert result == {
            ARWiFiBand.BAND_5G1: _METRICS,
            ARTrafficType.WIRED: _METRICS,
            ARTrafficType.BACKHAUL: _METRICS,
        }

    async def test_aggregate_without_callback(self) -> None:
        """Without a callback the aggregate yields nothing."""

        result = await get_state(
            AsyncMock(),
            ARTrafficAiMeshSource(target=_NODE),
            identity=_identity(),
            get_data_callback=None,
        )

        assert result == {}

    async def test_aggregate_no_node(self) -> None:
        """With no topology node only the WIRED link is probed."""

        captured: dict[str, Any] = {}

        async def fake_callback(sources: Any) -> dict[Any, Any]:
            captured["links"] = [src.link for src in sources]
            return {}

        await get_state(
            AsyncMock(),
            ARTrafficAiMeshSource(target=_NODE),
            identity=_identity(node=False),
            get_data_callback=fake_callback,
        )

        assert captured["links"] == [ARTrafficType.WIRED]

    async def test_aggregate_skips_non_dict_content(self) -> None:
        """Non-dict sub-results are ignored while merging."""

        async def fake_callback(sources: Any) -> dict[Any, Any]:
            return dict.fromkeys(sources)

        result = await get_state(
            AsyncMock(),
            ARTrafficAiMeshSource(target=_NODE),
            identity=_identity(),
            get_data_callback=fake_callback,
        )

        assert result == {}

    async def test_aggregate_non_dict_results(self) -> None:
        """A non-dict callback result yields an empty merge."""

        async def fake_callback(sources: Any) -> Any:
            return None

        result = await get_state(
            AsyncMock(),
            ARTrafficAiMeshSource(target=_NODE),
            identity=_identity(),
            get_data_callback=fake_callback,
        )

        assert result == {}


class TestTranslateState:
    """Tests for translate_state."""

    @pytest.mark.parametrize(
        "data",
        [None, "not-a-dict", 5],
        ids=["none", "str", "int"],
    )
    def test_bad_input(self, data: Any) -> None:
        """A non-dict input yields an empty result."""

        assert translate_state(data) == {}

    def test_translates_raw(self) -> None:
        """Atomic raw data maps to enum-keyed metrics, keyed by link."""

        result = translate_state({ARTrafficType.WIRED: _RAW})

        assert result == {ARTrafficType.WIRED: _METRICS}

    def test_passes_through_metrics(self) -> None:
        """Already-decoded metrics pass through unchanged."""

        data = {ARTrafficType.WIRED: _METRICS}

        assert translate_state(data) == data

    def test_empty_raw(self) -> None:
        """An empty raw value yields empty metrics for the link."""

        assert translate_state({ARTrafficType.WIRED: {}}) == {
            ARTrafficType.WIRED: {}
        }

    def test_empty_nested_raw(self) -> None:
        """A non-metrics raw that flattens to nothing yields empty."""

        assert translate_state({ARTrafficType.WIRED: {"data": {}}}) == {
            ARTrafficType.WIRED: {}
        }

    def test_drops_unknown_keys(self) -> None:
        """Unknown raw keys are dropped."""

        result = translate_state(
            {ARTrafficType.WIRED: {"weird": 1, "data": {"rx": 1}}}
        )

        assert result == {ARTrafficType.WIRED: {M.RX_SPEED: 1024.0}}

    def test_warns_on_bad_status(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A non-OK error status is logged as a warning."""

        with caplog.at_level(logging.WARNING):
            translate_state(
                {ARTrafficType.WIRED: {"data": {"rx": 1}, "error_status": 500}}
            )

        assert "500" in caplog.text


def test_flatten_dict() -> None:
    """Nested dicts flatten with `_`-joined keys; non-dicts yield empty."""

    nested: dict[str, Any] = {"a": {"b": {"c": 1}}, "d": {"e": 2}}
    assert aimesh._flatten_dict(nested) == {"a_b_c": 1, "d_e": 2}

    # None and other non-dict inputs yield an empty dict
    assert aimesh._flatten_dict(None) == {}
    assert aimesh._flatten_dict("not a dict") == {}

    # A non-dict value is kept as-is under its flattened key
    assert aimesh._flatten_dict({"a": {"b": 1}, "d": 2}) == {"a_b": 1, "d": 2}


def test_registers_callable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Importing the submodule registers the AiMesh source."""

    mock_register = Mock()
    monkeypatch.setattr(
        "asusrouter.registry.ARCallableRegistry.register_module",
        mock_register,
    )

    importlib.reload(aimesh)

    mock_register.assert_called_once_with(
        aimesh.ARTrafficAiMeshSource,
        get_state=aimesh.get_state,
        translate_state=aimesh.translate_state,
    )
