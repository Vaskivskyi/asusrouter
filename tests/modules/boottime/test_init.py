"""Tests for the boottime module."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import importlib
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from asusrouter.modules import boottime
from asusrouter.modules.boottime import (
    ARBoottime,
    ARBoottimeSource,
    _extract_uptime,
    get_state,
    read_uptime,
    stabilize,
)
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.source import ARDataSource

_WHEN = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
_BOOT = _WHEN - timedelta(seconds=100)


class TestReadUptime:
    """Tests for read_uptime."""

    def test_parses_boot_time(self) -> None:
        """Boot time = parsed `when` minus uptime, tagged as ARBoottime."""

        with patch.object(boottime, "safe_datetime", return_value=_WHEN):
            result = read_uptime("Jan 1 12:00:00 2026(100 secs)")

        assert result == _BOOT
        assert isinstance(result, ARBoottime)

    @pytest.mark.parametrize(
        "uptime",
        ["no-paren", "when(no digits)"],
        ids=["no_paren", "no_seconds"],
    )
    def test_unparseable(self, uptime: str) -> None:
        """Malformed strings yield None."""

        assert read_uptime(uptime) is None

    def test_bad_datetime(self) -> None:
        """An unparseable `when` yields None."""

        with patch.object(boottime, "safe_datetime", return_value=None):
            assert read_uptime("bad(100 secs)") is None


class TestSource:
    """Tests for ARBoottimeSource."""

    def test_is_data_source_all_equal(self) -> None:
        """All instances are equal and share a hash (router-global)."""

        assert issubclass(ARBoottimeSource, ARDataSource)
        assert ARBoottimeSource() == ARBoottimeSource()
        assert hash(ARBoottimeSource()) == hash(ARBoottimeSource())

    def test_not_equal_other_type(self) -> None:
        """Comparison to a non-source is not equal."""

        assert ARBoottimeSource() != "x"

    def test_repr(self) -> None:
        """Repr identifies the source."""

        assert repr(ARBoottimeSource()) == "<ARBoottimeSource>"


class TestStabilize:
    """Tests for the stabilize anchor function."""

    def test_first_sample(self) -> None:
        """Without a previous value the candidate is used."""

        assert stabilize(_BOOT, None) == _BOOT

    def test_keeps_within_jitter(self) -> None:
        """A sub-threshold change keeps the previous boot time."""

        assert stabilize(_BOOT + timedelta(seconds=1), _BOOT) == _BOOT

    def test_reboot(self) -> None:
        """A forward jump beyond the threshold is a new boot time."""

        rebooted = _BOOT + timedelta(seconds=5)
        assert stabilize(rebooted, _BOOT) == rebooted

    def test_none_candidate_keeps_previous(self) -> None:
        """A missing candidate keeps the previous boot time."""

        assert stabilize(None, _BOOT) == _BOOT

    def test_always_returns_boottime_type(self) -> None:
        """Even when keeping a plain-datetime prev, the result is tagged."""

        # prev is a plain datetime (e.g. a seed); jitter keeps it
        result = stabilize(_BOOT + timedelta(seconds=1), _BOOT)

        assert result == _BOOT
        assert isinstance(result, ARBoottime)


class TestARBoottime:
    """Tests for the ARBoottime datetime tag."""

    def test_from_datetime(self) -> None:
        """from_datetime preserves the value and is a datetime subclass."""

        tagged = ARBoottime.from_datetime(_BOOT)

        assert tagged == _BOOT
        assert isinstance(tagged, ARBoottime)
        assert isinstance(tagged, datetime)


class TestExtractUptime:
    """Tests for _extract_uptime (old-firmware raw fallback)."""

    def test_from_invalid_json(self) -> None:
        """The uptime value is pulled from the non-JSON old-FW response."""

        content = (
            '{\n"uptime":Sat, 01 Aug 2015 03:09:22 +0200'
            "(4162 secs since boot)\n}"
        )
        assert (
            _extract_uptime(content)
            == "Sat, 01 Aug 2015 03:09:22 +0200(4162 secs since boot)"
        )

    def test_quoted_value(self) -> None:
        """A quoted value is unquoted."""

        assert _extract_uptime('{"uptime":"when(1 secs)"}') == "when(1 secs)"

    @pytest.mark.parametrize("content", [None, 42, "{}", '{"other":1}'])
    def test_no_uptime(self, content: Any) -> None:
        """No usable uptime yields None."""

        assert _extract_uptime(content) is None


class TestGetState:
    """Tests for get_state."""

    async def test_raw_fallback(self) -> None:
        """When the JSON has no uptime, the raw content is parsed."""

        callback = AsyncMock(return_value={})
        raw_callback = AsyncMock(
            return_value='{\n"uptime":when(100 secs since boot)\n}'
        )

        with patch.object(boottime, "read_uptime", return_value=_BOOT):
            result = await get_state(
                callback,
                ARBoottimeSource(),
                raw_callback=raw_callback,
            )

        assert result == _BOOT
        raw_callback.assert_awaited_once()

    async def test_fetches_and_stabilizes(self) -> None:
        """Uptime is fetched and stabilized against the identity anchor."""

        callback = AsyncMock(return_value={"uptime": "when(100 secs)"})
        identity = ARDeviceIdentity()
        identity._boottime = _BOOT

        # A 1s jitter is absorbed: the identity's value is kept
        with patch.object(
            boottime, "read_uptime", return_value=_BOOT + timedelta(seconds=1)
        ):
            result = await get_state(
                callback, ARBoottimeSource(), identity=identity
            )

        assert result == _BOOT
        kwargs = callback.await_args.kwargs
        assert kwargs["endpoint"] == AREndpoint.FETCH_DATA
        assert kwargs["request"] == "hook=uptime()"

    async def test_without_identity(self) -> None:
        """With no identity the parsed candidate is returned directly."""

        callback = AsyncMock(return_value={"uptime": "when(100 secs)"})

        with patch.object(boottime, "read_uptime", return_value=_BOOT):
            result = await get_state(callback, ARBoottimeSource())

        assert result == _BOOT

    @pytest.mark.parametrize(
        "raw",
        [None, {}, {"other": 1}],
        ids=["non_dict", "empty", "no_uptime"],
    )
    async def test_missing_uptime(self, raw: Any) -> None:
        """A response without a usable uptime yields None."""

        callback = AsyncMock(return_value=raw)

        assert await get_state(callback, ARBoottimeSource()) is None


def test_registers_callable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Importing the module registers the boot time source."""

    mock_register = Mock()
    monkeypatch.setattr(
        "asusrouter.registry.ARCallableRegistry.register_module",
        mock_register,
    )

    importlib.reload(boottime)

    mock_register.assert_called_once_with(
        boottime.ARBoottimeSource,
        get_state=boottime.get_state,
    )
