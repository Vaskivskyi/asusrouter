"""Tests for the DSL module."""

from __future__ import annotations

import importlib
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from asusrouter.modules.common.metrics import ARMetricType
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.dsl import (
    ARDSLSource,
    fetch_state,
    source as dsl_source,
    translate_state,
)
from asusrouter.modules.dsl.source import _read_rate
from asusrouter.modules.nvram import ARNvramType
from asusrouter.modules.source import ARDataSource
from asusrouter.modules.support.flag import ARSupportType


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
    """Tests for fetch_state."""

    async def test_fetches_when_supported(self) -> None:
        """A DSL-capable device requests the rates from the NVRAM module."""

        values = {ARNvramType.DSL_DATARATE_DOWN: "1 Kbps"}
        get_data = AsyncMock(return_value=values)
        callback = AsyncMock()

        result = await fetch_state(
            callback,
            ARDSLSource(),
            fetch_data_callback=get_data,
            identity=_identity(dsl_support=True),
        )

        assert result == values
        callback.assert_not_awaited()
        assert get_data.await_args.args[0] == (
            ARNvramType.DSL_DATARATE_DOWN,
            ARNvramType.DSL_DATARATE_UP,
        )

    async def test_non_dict_response(self) -> None:
        """A non-dict response is normalized to an empty dict."""

        get_data = AsyncMock(return_value=None)

        result = await fetch_state(
            AsyncMock(),
            ARDSLSource(),
            fetch_data_callback=get_data,
            identity=_identity(dsl_support=True),
        )

        assert result == {}

    async def test_no_get_data_callback(self) -> None:
        """Without a data callback nothing is fetched."""

        callback = AsyncMock()

        result = await fetch_state(
            callback, ARDSLSource(), identity=_identity(dsl_support=True)
        )

        assert result == {}
        callback.assert_not_awaited()

    @pytest.mark.parametrize(
        "identity",
        [None, _identity(dsl_support=False)],
        ids=["no_identity", "unsupported"],
    )
    async def test_skips_without_support(
        self, identity: ARDeviceIdentity | None
    ) -> None:
        """No fetch happens without an identity or DSL support."""

        get_data = AsyncMock()

        result = await fetch_state(
            AsyncMock(),
            ARDSLSource(),
            fetch_data_callback=get_data,
            identity=identity,
        )

        assert result == {}
        get_data.assert_not_awaited()


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
        "asusrouter.registry.ARCallableRegistry.register_source",
        mock_register,
    )

    module = importlib.reload(dsl_source)

    mock_register.assert_called_once_with(
        module.ARDSLSource,
        fetch_state=module.fetch_state,
        translate_state=module.translate_state,
    )
