"""Tests for AsusRouter device probe coupling."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from asusrouter.asusrouter import AsusRouter
from asusrouter.modules.device import ARDeviceSourceUniversal
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.firmware.version import ARFirmware
from asusrouter.modules.source import ARDataSource
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.probe import ARProbeSection
from asusrouter.tools.security import ARSecurityLevel

_REDACTION = "best-effort"


def _written(path: Path) -> list[Path]:
    """List what a probe left in a directory."""

    return list(path.iterdir())


def _text(path: Path) -> str:
    """Read a written report back."""

    return path.read_text(encoding="utf-8")


class _ProbeSource(ARDataSource):
    """A source type carrying a probe."""


class _BareSource(ARDataSource):
    """A source type without a probe."""


@pytest.fixture
def probe_router(router: AsusRouter) -> AsusRouter:
    """Router with a complete device identity for probing."""

    identity = ARDeviceIdentity()
    identity._model = "RT-AX88U"
    identity._firmware = ARFirmware(
        major=(3, 0, 0, 4), minor=388, build=24762, revision=1
    )
    router._data_states[ARDeviceSourceUniversal] = Mock(content=identity)
    router._async_ensure_connected = AsyncMock()  # type: ignore[method-assign]
    return router


@pytest.fixture
def registered() -> Any:
    """Register a probe for `_ProbeSource` and report what it received."""

    seen: dict[str, Any] = {}

    async def probe(
        callback: Any, source: Any, **kwargs: Any
    ) -> list[ARProbeSection]:
        seen["source"] = source
        seen.update(kwargs)
        return [ARProbeSection("buffer", (("entries", "12"),))]

    ARCallReg.register_source(_ProbeSource, probe_state=probe)
    try:
        yield seen
    finally:
        ARCallReg.unregister(_ProbeSource)


class TestWarnProbeOnce:
    """Tests for _warn_probe_once."""

    def test_warns_only_once(
        self, router: AsusRouter, caplog: pytest.LogCaptureFixture
    ) -> None:
        """The redaction warning is emitted a single time."""

        with caplog.at_level(logging.WARNING):
            router._warn_probe_once()
            router._warn_probe_once()

        warnings = [r for r in caplog.records if _REDACTION in r.message]
        assert len(warnings) == 1


class TestAsyncProbeData:
    """Tests for async_probe_data."""

    async def test_writes_the_report(
        self, probe_router: AsusRouter, registered: Any, tmp_path: Path
    ) -> None:
        """A probed source produces a report on disk and in hand."""

        report = await probe_router.async_probe_data(
            _ProbeSource(), path=tmp_path
        )

        assert report is not None
        assert report.source == "_ProbeSource"
        assert report.level is ARSecurityLevel.SANITIZED
        assert report.sections[0].title == "buffer"

        written = _written(tmp_path)
        assert len(written) == 1
        assert "entries" in _text(written[0])

    async def test_without_a_path(
        self, probe_router: AsusRouter, registered: Any, tmp_path: Path
    ) -> None:
        """No path returns the report without touching the disk."""

        report = await probe_router.async_probe_data(_ProbeSource(), path=None)

        assert report is not None
        assert _written(tmp_path) == []

    async def test_passes_the_callbacks(
        self, probe_router: AsusRouter, registered: Any, tmp_path: Path
    ) -> None:
        """The probe is handed the fetch callbacks and the level."""

        await probe_router.async_probe_data(
            _ProbeSource(), path=tmp_path, level=ARSecurityLevel.STRICT
        )

        assert registered["level"] is ARSecurityLevel.STRICT
        assert callable(registered["fetch_data_callback"])
        assert callable(registered["fetch_raw_callback"])
        assert callable(registered["run_action_callback"])
        assert registered["identity"] is probe_router.description

    async def test_forces_a_fresh_fetch(
        self, probe_router: AsusRouter, registered: Any, tmp_path: Path
    ) -> None:
        """The bound fetch callback never serves a cached state."""

        seen: dict[str, Any] = {}

        async def fake_fetch(item: Any, force: bool = False) -> None:
            seen["force"] = force

        probe_router.async_fetch_data = fake_fetch  # type: ignore[method-assign]

        await probe_router.async_probe_data(_ProbeSource(), path=tmp_path)
        await registered["fetch_data_callback"](_ProbeSource())

        assert seen["force"] is True

    async def test_source_without_a_probe(
        self, probe_router: AsusRouter, tmp_path: Path
    ) -> None:
        """A source that registered no probe reports nothing."""

        report = await probe_router.async_probe_data(
            _BareSource(), path=tmp_path
        )

        assert report is None
        assert _written(tmp_path) == []
