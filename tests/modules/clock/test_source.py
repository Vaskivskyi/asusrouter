"""Tests for the clock source."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
import importlib
import pickle
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from asusrouter.modules.clock import (
    ARBoottime,
    ARClockField,
    ARClockSource,
    fetch_state,
    read_uptime,
    source as clock_source,
    stabilize,
)
from asusrouter.modules.clock.source import _extract_uptime
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.source import ARDataSource

_WHEN = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
_BOOT = _WHEN - timedelta(seconds=100)

# A real reply: the device states its clock, its offset and its uptime
_CEST = timezone(timedelta(hours=2))
_UPTIME = "Fri, 31 Jul 2026 10:24:04 +0200(2131043 secs since boot)"


class TestReadUptime:
    """Tests for read_uptime."""

    def test_reads_all_three_values(self) -> None:
        """The device clock, its uptime and the boot time between them."""

        assert read_uptime(_UPTIME) == {
            ARClockField.BOOTTIME: ARBoottime(
                2026, 7, 6, 18, 26, 41, tzinfo=_CEST
            ),
            ARClockField.DEVICE_TIME: datetime(
                2026, 7, 31, 10, 24, 4, tzinfo=_CEST
            ),
            ARClockField.UPTIME: 2131043,
        }

    def test_device_time_keeps_the_offset(self) -> None:
        """The device states the zone it runs on; it is not dropped."""

        device_time = read_uptime(_UPTIME)[ARClockField.DEVICE_TIME]

        assert device_time.tzinfo is not None
        assert device_time.utcoffset() == timedelta(hours=2)

    def test_boot_time_is_tagged(self) -> None:
        """The boot time carries the tag the identity sync looks for."""

        assert isinstance(
            read_uptime(_UPTIME)[ARClockField.BOOTTIME], ARBoottime
        )

    @pytest.mark.parametrize(
        "uptime",
        ["no-paren", "when(no digits)"],
        ids=["no_paren", "no_seconds"],
    )
    def test_unparseable(self, uptime: str) -> None:
        """Malformed strings yield no values at all."""

        assert read_uptime(uptime) == {}

    @pytest.mark.parametrize(
        "uptime",
        [
            # Parses as nothing at all
            "Fri, 31 Jul 2026 10:24:04(100 secs)",
            # Parses, but naive: ISO with no offset
            "2026-07-31T10:24:04(100 secs)",
        ],
        ids=["unparseable", "naive"],
    )
    def test_clock_without_an_offset(self, uptime: str) -> None:
        """A clock that states no offset yields only the uptime."""

        assert read_uptime(uptime) == {ARClockField.UPTIME: 100}

    @pytest.mark.parametrize(
        "seconds",
        # Past a century, and past what a timedelta can even hold
        ["99999999999999", "9" * 400],
        ids=["absurd", "past_timedelta"],
    )
    def test_uptime_beyond_any_device(self, seconds: str) -> None:
        """A count no device could reach is a malformed reply, not data."""

        content = f"Fri, 31 Jul 2026 10:24:04 +0200({seconds} secs)"

        assert read_uptime(content) == {}

    @pytest.mark.parametrize(
        "when",
        ["Mon, 01 Jan 0001 00:00:00 +0000", "Sat, 01 Jan 0050 00:00:00 +0000"],
        ids=["year_one", "year_fifty"],
    )
    def test_clock_too_early_for_its_own_uptime(self, when: str) -> None:
        """Subtracting past the calendar keeps the count, not a boot time."""

        assert read_uptime(f"{when}(3153600000 secs)") == {
            ARClockField.UPTIME: 3153600000
        }

    def test_a_long_but_possible_uptime(self) -> None:
        """A device up for years is still read, not rejected as absurd."""

        five_years = 5 * 365 * 24 * 3600
        content = f"Fri, 31 Jul 2026 10:24:04 +0200({five_years} secs)"

        assert read_uptime(content)[ARClockField.UPTIME] == five_years


class TestSource:
    """Tests for ARClockSource."""

    def test_is_data_source_all_equal(self) -> None:
        """All instances are equal and share a hash (router-global)."""

        assert issubclass(ARClockSource, ARDataSource)
        assert ARClockSource() == ARClockSource()
        assert hash(ARClockSource()) == hash(ARClockSource())

    def test_not_equal_other_type(self) -> None:
        """Comparison to a non-source is not equal."""

        assert ARClockSource() != "x"

    def test_repr(self) -> None:
        """Repr identifies the source."""

        assert repr(ARClockSource()) == "<ARClockSource>"


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

    @pytest.mark.parametrize(
        ("candidate", "prev", "expected"),
        [
            (_BOOT, datetime(2026, 1, 1, 11, 58, 20), _BOOT),
            (datetime(2026, 1, 1, 11, 58, 20), _BOOT, _BOOT),
            (None, datetime(2026, 1, 1, 11, 58, 20), None),
            (datetime(2026, 1, 1, 11, 58, 20), None, None),
        ],
        ids=["naive_prev", "naive_candidate", "naive_prev_only", "naive_only"],
    )
    def test_naive_never_passes_through(
        self,
        candidate: datetime | None,
        prev: datetime | None,
        expected: datetime | None,
    ) -> None:
        """A time stating no offset is never handed on as a boot time."""

        result = stabilize(candidate, prev)

        assert result == expected
        assert result is None or result.tzinfo is not None

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

    def test_naive_is_rejected(self) -> None:
        """The tag carries the invariant: a boot time states its offset."""

        with pytest.raises(ValueError, match="must state its offset"):
            ARBoottime(2026, 1, 1)

    def test_naive_from_datetime_is_rejected(self) -> None:
        """Tagging a naive datetime is a bug, not a value to pass on."""

        with pytest.raises(ValueError, match="must state its offset"):
            ARBoottime.from_datetime(datetime(2026, 1, 1))

    def test_survives_a_round_trip(self) -> None:
        """Pickling and replacing keep both the tag and the offset."""

        tagged = ARBoottime.from_datetime(_BOOT)
        restored = pickle.loads(pickle.dumps(tagged))

        assert restored == tagged
        assert isinstance(restored, ARBoottime)
        assert tagged.replace(year=2027).tzinfo is not None


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
    """Tests for fetch_state."""

    async def test_raw_fallback(self) -> None:
        """When the JSON has no uptime, the raw content is parsed."""

        callback = AsyncMock(return_value={})
        fetch_raw_callback = AsyncMock(
            return_value=f'{{\n"uptime":{_UPTIME}\n}}'
        )

        result = await fetch_state(
            callback,
            ARClockSource(),
            fetch_raw_callback=fetch_raw_callback,
        )

        assert result[ARClockField.UPTIME] == 2131043
        fetch_raw_callback.assert_awaited_once()
        # The raw read answered, so the same hook is not asked twice
        callback.assert_not_awaited()

    async def test_fetches_and_stabilizes(self) -> None:
        """Uptime is fetched and stabilized against the identity anchor."""

        callback = AsyncMock(return_value={"uptime": _UPTIME})
        identity = ARDeviceIdentity()
        # A 1s jitter is absorbed: the identity's value is kept
        anchor = ARBoottime(2026, 7, 6, 18, 26, 40, tzinfo=_CEST)
        identity._boottime = anchor

        result = await fetch_state(
            callback, ARClockSource(), identity=identity
        )

        assert result[ARClockField.BOOTTIME] == anchor
        kwargs = callback.await_args.kwargs
        assert kwargs["endpoint"] == AREndpoint.FETCH_DATA
        assert kwargs["request"] == "hook=uptime()"

    async def test_without_identity(self) -> None:
        """With no identity the parsed boot time is returned directly."""

        callback = AsyncMock(return_value={"uptime": _UPTIME})

        result = await fetch_state(callback, ARClockSource())

        assert result[ARClockField.BOOTTIME] == ARBoottime(
            2026, 7, 6, 18, 26, 41, tzinfo=_CEST
        )

    async def test_naive_anchor_is_not_compared(self) -> None:
        """An anchor that cannot be measured leaves the fresh read to win."""

        callback = AsyncMock(return_value={"uptime": _UPTIME})
        identity = ARDeviceIdentity()
        # A naive seed cannot be subtracted from an aware candidate
        identity._boottime = datetime(2026, 7, 6, 18, 26, 40)

        result = await fetch_state(
            callback, ARClockSource(), identity=identity
        )

        assert result[ARClockField.BOOTTIME] == ARBoottime(
            2026, 7, 6, 18, 26, 41, tzinfo=_CEST
        )

    @pytest.mark.parametrize(
        "raw",
        [None, {}, {"other": 1}],
        ids=["non_dict", "empty", "no_uptime"],
    )
    async def test_missing_uptime(self, raw: Any) -> None:
        """A response without a usable uptime yields no values."""

        callback = AsyncMock(return_value=raw)

        assert await fetch_state(callback, ARClockSource()) == {}


def test_registers_callable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Importing the module registers the boot time source."""

    mock_register = Mock()
    monkeypatch.setattr(
        "asusrouter.registry.ARCallableRegistry.register_source",
        mock_register,
    )

    module = importlib.reload(clock_source)

    mock_register.assert_called_once_with(
        module.ARClockSource,
        fetch_state=module.fetch_state,
    )
