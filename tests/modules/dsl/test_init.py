"""Tests for the DSL module."""

from __future__ import annotations

import importlib
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from asusrouter.modules import dsl
from asusrouter.modules.common.metrics import ARMetricType
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.dsl import (
    ARDSLSource,
    _read_rate,
    get_state,
    translate_state,
)
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.source import ARDataSource
from asusrouter.modules.support.flag import ARSupportType

_REQUEST = "hook=nvram_get(dsllog_dataratedown);nvram_get(dsllog_datarateup)"


def _identity(*, dsl_support: bool) -> ARDeviceIdentity:
    """Build an identity with the DSL support flag set as given."""

    identity = ARDeviceIdentity()
    identity._support = {ARSupportType.DSL: dsl_support}
    return identity


class TestReadRate:
    """Tests for _read_rate."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("12345 Kbps", 12345000.0),
            ("12345", 12345000.0),
            (12345, 12345000.0),
            ("0 Kbps", 0.0),
        ],
    )
    def test_reads_bits_per_second(self, value: Any, expected: float) -> None:
        """A `<n> Kbps` value converts to bits per second."""

        assert _read_rate(value) == expected

    @pytest.mark.parametrize("value", [None, "", "N/A", "-- Kbps"])
    def test_unparseable(self, value: Any) -> None:
        """Missing or non-numeric values yield None."""

        assert _read_rate(value) is None


class TestSource:
    """Tests for ARDSLSource."""

    def test_is_data_source_all_equal(self) -> None:
        """All instances are equal and share a hash (router-global)."""

        assert issubclass(ARDSLSource, ARDataSource)
        assert ARDSLSource() == ARDSLSource()
        assert hash(ARDSLSource()) == hash(ARDSLSource())

    def test_not_equal_other_type(self) -> None:
        """Comparison to a non-source is not equal."""

        assert ARDSLSource() != "x"

    def test_repr(self) -> None:
        """Repr identifies the source."""

        assert repr(ARDSLSource()) == "<ARDSLSource>"


class TestGetState:
    """Tests for get_state."""

    async def test_fetches_when_supported(self) -> None:
        """A DSL-capable device fetches the data rate nvram keys."""

        callback = AsyncMock(return_value={"dsllog_dataratedown": "1 Kbps"})

        result = await get_state(
            callback, ARDSLSource(), identity=_identity(dsl_support=True)
        )

        assert result == {"dsllog_dataratedown": "1 Kbps"}
        kwargs = callback.await_args.kwargs
        assert kwargs["endpoint"] == AREndpoint.FETCH_DATA
        assert kwargs["request"] == _REQUEST

    async def test_non_dict_response(self) -> None:
        """A non-dict response is normalized to an empty dict."""

        callback = AsyncMock(return_value=None)

        result = await get_state(
            callback, ARDSLSource(), identity=_identity(dsl_support=True)
        )

        assert result == {}

    @pytest.mark.parametrize(
        "identity",
        [None, _identity(dsl_support=False)],
        ids=["no_identity", "unsupported"],
    )
    async def test_skips_without_support(
        self, identity: ARDeviceIdentity | None
    ) -> None:
        """No fetch happens without an identity or DSL support."""

        callback = AsyncMock()

        result = await get_state(callback, ARDSLSource(), identity=identity)

        assert result == {}
        callback.assert_not_awaited()


class TestTranslateState:
    """Tests for translate_state."""

    def test_translates_both_directions(self) -> None:
        """Both data rates map to their metric in bits per second."""

        result = translate_state(
            {
                "dsllog_dataratedown": "12345 Kbps",
                "dsllog_datarateup": "678 Kbps",
            }
        )

        assert result == {
            ARMetricType.DOWNLOAD_SPEED: 12345000.0,
            ARMetricType.UPLOAD_SPEED: 678000.0,
        }

    def test_skips_missing_fields(self) -> None:
        """Absent or unparseable fields are omitted, not zeroed."""

        result = translate_state({"dsllog_dataratedown": "5 Kbps"})

        assert result == {ARMetricType.DOWNLOAD_SPEED: 5000.0}

    @pytest.mark.parametrize("data", [None, "x", 42, {}])
    def test_no_data(self, data: Any) -> None:
        """Non-dict or empty input yields an empty result."""

        assert translate_state(data) == {}


def test_registers_callable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Importing the module registers the DSL source."""

    mock_register = Mock()
    monkeypatch.setattr(
        "asusrouter.registry.ARCallableRegistry.register_module",
        mock_register,
    )

    importlib.reload(dsl)

    mock_register.assert_called_once_with(
        dsl.ARDSLSource,
        get_state=dsl.get_state,
        translate_state=dsl.translate_state,
    )
