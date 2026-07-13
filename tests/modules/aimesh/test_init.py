"""Tests for the AiMesh module source and callables."""

from __future__ import annotations

import importlib
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from asusrouter.modules.aimesh import (
    ARAiMeshSource,
    ARAiMeshSourceUniversal,
    ARAiMeshTopology,
    get_state,
    source as aimesh_source,
    translate_state,
)
from asusrouter.modules.endpoint_v2 import AREndpoint, get_endpoint_reader
from asusrouter.modules.source import ARDataSource
from asusrouter.tools.readers import read_js_variables

_RAW = (
    'get_cfg_clientlist = [[{"mac":"AA:00:00:00:00:00","online":"1",'
    '"level":"0","re_path":"0","ap2g":"AA:00:00:00:00:10"}]][0];\n'
)


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
    """Tests for get_state."""

    async def test_fetches_onboarding(self) -> None:
        """get_state fetches the onboarding endpoint and returns the dict."""

        callback = AsyncMock(return_value={"get_cfg_clientlist": [[]]})

        result = await get_state(callback, ARAiMeshSourceUniversal)

        callback.assert_awaited_once_with(endpoint=AREndpoint.FETCH_ONBOARDING)
        assert result == {"get_cfg_clientlist": [[]]}

    async def test_non_dict_response(self) -> None:
        """A non-dict response yields an empty dict."""

        callback = AsyncMock(return_value="not-a-dict")

        assert await get_state(callback, ARAiMeshSourceUniversal) == {}


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
        "asusrouter.registry.ARCallableRegistry.register_module",
        mock_register,
    )

    module = importlib.reload(aimesh_source)

    mock_register.assert_called_once()
    args, kwargs = mock_register.call_args
    assert args[0] is module.ARAiMeshSource
    assert kwargs == {
        "get_state": module.get_state,
        "translate_state": module.translate_state,
    }
