"""Tests for AsusRouter data dump coupling."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from asusrouter.asusrouter import AsusRouter
from asusrouter.const import RequestType
from asusrouter.error import AsusRouterError
from asusrouter.modules.ddns.source import ARDdnsSource
from asusrouter.modules.device import ARDeviceSourceUniversal
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.firmware.version import ARFirmware
from asusrouter.modules.led import ARLedSource
from asusrouter.modules.source import ARDataSource
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.dump.recorder import (
    ARDumpRecorder,
    active_recorder,
    bind_recorder,
    unbind_recorder,
)

_SENSITIVE = "sensitive information"


def _noop_fetch(*args: Any, **kwargs: Any) -> dict[Any, Any]:
    """Return an empty fetch_state result for registering fake sources."""

    return {}


class _DumpSource(ARDataSource):
    """A distinct source type for dump tests."""


class _AltDumpSource(ARDataSource):
    """A second distinct source type for dump tests."""


class _ThirdDumpSource(ARDataSource):
    """A third distinct source type for dump tests."""


@pytest.fixture
def dump_router(router: AsusRouter) -> AsusRouter:
    """Router with a complete device identity for dumping."""

    identity = ARDeviceIdentity()
    identity._model = "RT-AX88U"
    identity._firmware = ARFirmware(
        major=(3, 0, 0, 4), minor=388, build=24762, revision=1
    )
    router._data_states[ARDeviceSourceUniversal] = Mock(content=identity)
    return router


class TestAsyncFetchRecording:
    """Tests for the raw-request tee in async_fetch."""

    async def test_records_when_dumping(self, router: AsusRouter) -> None:
        """A wire reply is recorded while a recorder is active."""

        router._connection.async_query = AsyncMock(  # type: ignore[method-assign]
            return_value=(200, {}, "body")
        )
        recorder = ARDumpRecorder()
        token = bind_recorder(recorder)
        try:
            result = await router.async_fetch(AREndpoint.FETCH_DATA, "p")
        finally:
            unbind_recorder(token)

        assert result == "body"
        assert len(recorder) == 1
        recorded = recorder.requests[0]
        assert recorded.endpoint is AREndpoint.FETCH_DATA
        assert recorded.payload == "p"
        assert recorded.content == "body"


class TestWarnDumpOnce:
    """Tests for _warn_dump_once."""

    def test_warns_only_once(
        self, router: AsusRouter, caplog: pytest.LogCaptureFixture
    ) -> None:
        """The sensitive-data warning is emitted a single time."""

        with caplog.at_level(logging.WARNING):
            router._warn_dump_once()
            router._warn_dump_once()

        warnings = [r for r in caplog.records if _SENSITIVE in r.message]
        assert len(warnings) == 1


class TestAsyncDumpData:
    """Tests for async_dump_data."""

    async def test_writes_scenario(
        self, dump_router: AsusRouter, tmp_path: Path
    ) -> None:
        """Dumps a source's raw replies to disk."""

        async def fake_fetch(item: Any, force: bool) -> None:
            assert force is True
            recorder = active_recorder()
            assert recorder is not None
            recorder.record(
                AREndpoint.FETCH_DATA, RequestType.POST, "p", "body"
            )

        dump_router.async_fetch_data = fake_fetch  # type: ignore[method-assign]

        result = await dump_router.async_dump_data(
            _DumpSource(), path=tmp_path
        )

        assert len(result) == 1
        assert (result[0] / "00.content").read_text("utf-8") == "body"
        # The recorder is unbound after the dump
        assert active_recorder() is None

    async def test_writes_device_snapshot(
        self, dump_router: AsusRouter, tmp_path: Path
    ) -> None:
        """A successful dump also emits the device context snapshot."""

        async def fake_fetch(item: Any, force: bool) -> None:
            recorder = active_recorder()
            assert recorder is not None
            recorder.record(
                AREndpoint.FETCH_DATA, RequestType.POST, "p", "body"
            )

        dump_router.async_fetch_data = fake_fetch  # type: ignore[method-assign]

        await dump_router.async_dump_data(_DumpSource(), path=tmp_path)

        device = tmp_path / "RT-AX88U" / "3.0.0.4.388.24762_1" / "device.json"
        assert device.is_file()

    async def test_empty_request(
        self, dump_router: AsusRouter, tmp_path: Path
    ) -> None:
        """A request that yields no collection writes nothing."""

        result = await dump_router.async_dump_data(
            "not-a-source",  # type: ignore[arg-type]
            path=tmp_path,
        )

        assert result == []

    async def test_skips_when_nothing_recorded(
        self, dump_router: AsusRouter, tmp_path: Path
    ) -> None:
        """A source with no wire traffic produces no files."""

        async def fake_fetch(item: Any, force: bool) -> None:
            return None

        dump_router.async_fetch_data = fake_fetch  # type: ignore[method-assign]

        result = await dump_router.async_dump_data(
            _DumpSource(), path=tmp_path
        )

        assert result == []

    async def test_collection_warns_once(
        self,
        dump_router: AsusRouter,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Dumping many sources warns once and writes one dir per source."""

        async def fake_fetch(item: Any, force: bool) -> None:
            recorder = active_recorder()
            assert recorder is not None
            recorder.record(AREndpoint.FETCH_DATA, RequestType.POST, "p", "b")

        dump_router.async_fetch_data = fake_fetch  # type: ignore[method-assign]

        with caplog.at_level(logging.WARNING):
            result = await dump_router.async_dump_data(
                [_DumpSource(), _AltDumpSource()], path=tmp_path
            )

        assert len(result) == 2
        assert {path.parent.name for path in result} == {
            "_DumpSource",
            "_AltDumpSource",
        }
        warnings = [r for r in caplog.records if _SENSITIVE in r.message]
        assert len(warnings) == 1


class TestDefaultSources:
    """Tests for _default_sources."""

    def test_builds_source_instances(self, router: AsusRouter) -> None:
        """Returns default instances of every registered fetchable source."""

        sources = router._default_sources()
        classes = {type(item) for item in sources}

        assert all(isinstance(item, ARDataSource) for item in sources)
        assert ARLedSource in classes
        # A source whose module is not eagerly imported is discovered too
        assert ARDdnsSource in classes

    def test_skips_argful_and_non_source(self, router: AsusRouter) -> None:
        """Skips sources without a no-arg default and non-source classes."""

        class _NeedsArgs(ARDataSource):
            def __init__(self, required: Any) -> None:
                super().__init__()

        class _NotSource:
            pass

        ARCallReg.register_source(_NeedsArgs, fetch_state=_noop_fetch)
        ARCallReg.register_source(_NotSource, fetch_state=_noop_fetch)
        try:
            classes = {type(item) for item in router._default_sources()}
        finally:
            ARCallReg.unregister(_NeedsArgs)
            ARCallReg.unregister(_NotSource)

        assert _NeedsArgs not in classes
        assert _NotSource not in classes


class TestAsyncDumpAll:
    """Tests for async_dump_all."""

    async def test_dumps_and_skips_failures(
        self,
        dump_router: AsusRouter,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Dumps every default source, skipping empty and failing ones."""

        ok, failing, empty = (
            _DumpSource(),
            _AltDumpSource(),
            _ThirdDumpSource(),
        )
        dump_router._default_sources = lambda: [  # type: ignore[method-assign]
            ok,
            failing,
            empty,
        ]

        async def fake_fetch(item: Any, force: bool) -> None:
            if type(item) is _AltDumpSource:
                raise AsusRouterError("boom")
            if type(item) is _DumpSource:
                recorder = active_recorder()
                assert recorder is not None
                recorder.record(
                    AREndpoint.FETCH_DATA, RequestType.POST, "p", "b"
                )

        dump_router.async_fetch_data = fake_fetch  # type: ignore[method-assign]

        with caplog.at_level(logging.WARNING):
            result = await dump_router.async_dump_all(path=tmp_path)

        assert len(result) == 1
        assert result[0].parent.name == "_DumpSource"
        warnings = [r for r in caplog.records if _SENSITIVE in r.message]
        assert len(warnings) == 1
