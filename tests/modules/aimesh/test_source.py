"""Tests for the AiMesh source."""

from __future__ import annotations

import importlib
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from asusrouter.modules.aimesh import (
    ARAiMeshSource,
    ARAiMeshSourceUniversal,
    ARAiMeshTopology,
    fetch_state,
    source as aimesh_source,
    translate_state,
)
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.endpoint import AREndpoint, get_endpoint_reader
from asusrouter.modules.source import ARDataSource
from asusrouter.modules.support.flag import ARSupportType
from asusrouter.tools.readers import read_js_variables

_RAW = (
    'get_cfg_clientlist = [[{"mac":"AA:00:00:00:00:00","online":"1",'
    '"level":"0","re_path":"0","ap2g":"AA:00:00:00:00:10"}]][0];\n'
)


def _identity(*, aimesh: bool = True) -> ARDeviceIdentity:
    """Build an identity with the AiMesh support flag set."""

    identity = ARDeviceIdentity()
    identity._support[ARSupportType.AIMESH] = aimesh
    return identity


class TestARAiMeshSource:
    """Tests for the AiMesh source."""

    def test_is_data_source(self) -> None:
        """The source subclasses ARDataSource."""

        assert issubclass(ARAiMeshSource, ARDataSource)

    def test_dedup_by_type(self) -> None:
        """Sources are equal and hash equal (no defining properties)."""

        assert ARAiMeshSource() == ARAiMeshSource()
        assert hash(ARAiMeshSource()) == hash(ARAiMeshSource())
        assert len({ARAiMeshSource(), ARAiMeshSource()}) == 1

    def test_not_equal_other_type(self) -> None:
        """Comparison to a non-source is not equal."""

        assert ARAiMeshSource() != "not-a-source"

    def test_repr(self) -> None:
        """Repr names the source."""

        assert repr(ARAiMeshSource()) == "<ARAiMeshSource>"


class TestGetState:
    """Tests for fetch_state."""

    async def test_fetches_onboarding(self) -> None:
        """fetch_state fetches the onboarding endpoint and returns the dict."""

        callback = AsyncMock(return_value={"get_cfg_clientlist": [[]]})

        result = await fetch_state(
            callback, ARAiMeshSourceUniversal, identity=_identity()
        )

        callback.assert_awaited_once_with(endpoint=AREndpoint.FETCH_ONBOARDING)
        assert result == {"get_cfg_clientlist": [[]]}

    async def test_non_dict_response(self) -> None:
        """A non-dict response yields an empty dict."""

        callback = AsyncMock(return_value="not-a-dict")

        assert (
            await fetch_state(
                callback, ARAiMeshSourceUniversal, identity=_identity()
            )
            == {}
        )

    async def test_unsupported_skips_fetch(self) -> None:
        """Without AiMesh support nothing is fetched."""

        callback = AsyncMock()

        result = await fetch_state(
            callback, ARAiMeshSourceUniversal, identity=_identity(aimesh=False)
        )

        assert result == {}
        callback.assert_not_awaited()

    async def test_no_identity_skips_fetch(self) -> None:
        """Without an identity nothing is fetched."""

        callback = AsyncMock()

        assert await fetch_state(callback, ARAiMeshSourceUniversal) == {}
        callback.assert_not_awaited()


class TestTranslateState:
    """Tests for translate_state."""

    def test_builds_topology(self) -> None:
        """Onboarding data becomes an ARAiMeshTopology."""

        data = read_js_variables(_RAW)

        topo = translate_state(data)

        assert isinstance(topo, ARAiMeshTopology)
        assert topo.root() is not None

    def test_status_and_onboarding(self) -> None:
        """Onboarding status and the raw onboarding list are wired in."""

        raw = _RAW + (
            'get_onboardingstatus = [{"cfg_ready":"1",'
            '"cfg_re_maxnum":"16","cfg_obrssi":"-20"}][0];\n'
            "get_onboardinglist = [{}][0];\n"
        )

        topo = translate_state(read_js_variables(raw))

        assert topo.status.ready is True
        assert topo.status.re_maxnum == 16
        assert topo.status.rssi == -20
        assert topo.onboarding == {}

    @pytest.mark.parametrize(
        "data",
        [
            "not-a-dict",
            {},
            {"get_cfg_clientlist": []},
            {"get_cfg_clientlist": "x"},
        ],
        ids=["str", "empty", "empty_list", "not_list"],
    )
    def test_empty_or_bad(self, data: Any) -> None:
        """Bad or empty data yields an empty topology."""

        assert translate_state(data).nodes == {}


def test_reader_registered() -> None:
    """The onboarding endpoint uses the JS-variable reader."""

    assert (
        get_endpoint_reader(AREndpoint.FETCH_ONBOARDING) is read_js_variables
    )


def test_registers_callables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Importing the module registers the source callables."""

    mock_register = Mock()
    monkeypatch.setattr(
        "asusrouter.registry.ARCallableRegistry.register_source",
        mock_register,
    )

    module = importlib.reload(aimesh_source)

    mock_register.assert_called_once()
    args, kwargs = mock_register.call_args
    assert args[0] is module.ARAiMeshSource
    assert kwargs == {
        "fetch_state": module.fetch_state,
        "translate_state": module.translate_state,
    }
