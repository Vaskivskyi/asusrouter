"""Tests for the log source."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock

import pytest

from asusrouter.config import (
    ARConfig,
    ARConfigKey as ARConfKey,
    ARInstanceConfig,
)
from asusrouter.modules.clock import ARClockSourceUniversal
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.log.entry import ARLogProgram
from asusrouter.modules.log.enums import ARLogField
from asusrouter.modules.log.source import (
    _LOG_HOOK,
    ARLogSource,
    fetch_state,
    translate_state,
)
from asusrouter.tools.identifiers import MacAddress, Username
from asusrouter.tools.security import ARSecurityLevel
from asusrouter.tools.security.text import SensitiveText

_RAW = '{"nvram_dump-syslog.log":Jul 21 15:08:01 kernel: boot}'
# A cleared log: the wrapper is served, it just holds no records
_RAW_EMPTY = '{"nvram_dump-syslog.log":}'


class TestFetchState:
    """Fetching the raw log through the single hook call."""

    async def test_fetched(self) -> None:
        """The hook reply is returned as-is, in one request."""

        raw = AsyncMock(return_value=_RAW)

        result = await fetch_state(
            AsyncMock(), ARLogSource(), fetch_raw_callback=raw
        )

        assert "kernel: boot" in result
        raw.assert_awaited_once()
        assert raw.await_args.kwargs["endpoint"] is AREndpoint.FETCH_DATA

    async def test_clock_read_when_identity_has_none(self) -> None:
        """A device that never answered the clock is asked again."""

        fetch_data = AsyncMock()

        await fetch_state(
            AsyncMock(),
            ARLogSource(),
            fetch_raw_callback=AsyncMock(return_value=_RAW),
            fetch_data_callback=fetch_data,
            identity=ARDeviceIdentity(),
        )

        fetch_data.assert_awaited_once_with(ARClockSourceUniversal)

    async def test_clock_not_reread_when_current(self) -> None:
        """A clock near the host's is trusted; no request is spent."""

        identity = ARDeviceIdentity()
        identity.update_device_time(datetime.now(UTC) - timedelta(hours=2))
        fetch_data = AsyncMock()

        await fetch_state(
            AsyncMock(),
            ARLogSource(),
            fetch_raw_callback=AsyncMock(return_value=_RAW),
            fetch_data_callback=fetch_data,
            identity=identity,
        )

        fetch_data.assert_not_awaited()

    @pytest.mark.parametrize(
        "device_time",
        [
            datetime(1970, 1, 1, tzinfo=UTC),
            datetime(2099, 1, 1, tzinfo=UTC),
        ],
        ids=["never_synced", "far_ahead"],
    )
    async def test_clock_reread_when_far_from_the_host(
        self, device_time: datetime
    ) -> None:
        """A clock this far out has not synced; it may have since.

        Entries the device writes after syncing would otherwise be dated
        by the stale reading.
        """

        identity = ARDeviceIdentity()
        identity.update_device_time(device_time)
        fetch_data = AsyncMock()

        await fetch_state(
            AsyncMock(),
            ARLogSource(),
            fetch_raw_callback=AsyncMock(return_value=_RAW),
            fetch_data_callback=fetch_data,
            identity=identity,
        )

        fetch_data.assert_awaited_once_with(ARClockSourceUniversal)

    async def test_clock_reread_when_it_states_no_offset(self) -> None:
        """A clock with no offset cannot be measured against the host."""

        identity = ARDeviceIdentity()
        identity.update_device_time(datetime.now())
        fetch_data = AsyncMock()

        await fetch_state(
            AsyncMock(),
            ARLogSource(),
            fetch_raw_callback=AsyncMock(return_value=_RAW),
            fetch_data_callback=fetch_data,
            identity=identity,
        )

        fetch_data.assert_awaited_once_with(ARClockSourceUniversal)

    async def test_no_raw_callback(self) -> None:
        """Without a raw callback there is nothing to fetch."""

        result = await fetch_state(
            AsyncMock(), ARLogSource(), fetch_raw_callback=None
        )

        assert result == ""

    async def test_empty_reply(self) -> None:
        """An empty reply yields an empty string."""

        raw = AsyncMock(return_value=None)

        result = await fetch_state(
            AsyncMock(), ARLogSource(), fetch_raw_callback=raw
        )

        assert result == ""

    async def test_requested_hook(self) -> None:
        """The single hook call carries both log arguments."""

        raw = AsyncMock(return_value=_RAW)

        await fetch_state(AsyncMock(), ARLogSource(), fetch_raw_callback=raw)

        request = raw.await_args.kwargs["request"]
        assert _LOG_HOOK[0].value in request
        assert "syslog.log" in request

    async def test_wrapper_without_records(self) -> None:
        """A cleared log still answers with the wrapper and is kept."""

        raw = AsyncMock(return_value=_RAW_EMPTY)

        result = await fetch_state(
            AsyncMock(), ARLogSource(), fetch_raw_callback=raw
        )

        assert result == _RAW_EMPTY
        raw.assert_awaited_once()


class TestTranslateState:
    """Turning raw text into the log data dict."""

    def test_parses_text(self) -> None:
        """A raw string becomes the lean dict (entries + monitor signals)."""

        result = translate_state(_RAW)

        entries = result[ARLogField.ENTRY_LIST]
        assert len(entries) == 1
        entry = entries[0]
        assert entry.timestamp_str == "Jul 21 15:08:01"
        assert entry.program == ARLogProgram("kernel")
        assert entry.content.value == "boot"
        # translate resolves the datetime (3c), unlike bare parse_log
        assert entry.timestamp is not None
        # monitor signals
        assert result[ARLogField.LAST_ENTRY] == entry.timestamp
        assert result[ARLogField.ENTRY_COUNT] == 1

    def test_no_program_list(self) -> None:
        """The lean translate output omits the costly program grouping."""

        result = translate_state(_RAW)

        assert ARLogField.PROGRAM_LIST not in result

    def test_keys_are_enums(self) -> None:
        """The data dict is keyed only by ARLogField members, never str."""

        result = translate_state(_RAW)

        assert all(isinstance(key, ARLogField) for key in result)

    def test_non_string(self) -> None:
        """Non-string data yields empty collections and no last entry."""

        result = translate_state({"unexpected": True})

        assert result[ARLogField.ENTRY_LIST] == []
        assert result[ARLogField.LAST_ENTRY] is None
        assert result[ARLogField.ENTRY_COUNT] == 0


def _log(*records: str) -> str:
    """Wrap raw records the way the device serves them.

    The device closes its buffer with a blank line, and the next read
    has records where that line used to be - so a fixture without it
    cannot show whether one read continues the previous one.
    """

    return '{"nvram_dump-syslog.log":' + "\n".join(records) + "\n\n}"


def _records(first: int, last: int) -> list[str]:
    """Build a run of distinct records."""

    return [
        f"Jul 21 {index // 3600:02d}:{index // 60 % 60:02d}:{index % 60:02d} "
        f"kernel: line {index}"
        for index in range(first, last)
    ]


class TestContinuedRead:
    """Reading only what is new since the previous read."""

    def test_appends_new_records(self) -> None:
        """A second read adds the new records to the ones already held."""

        first = translate_state(_log(*_records(0, 40)))
        second = translate_state(_log(*_records(0, 45)), previous=first)

        entries = second[ARLogField.ENTRY_LIST]
        assert len(entries) == 45
        assert entries[0].content.value == "line 0"
        assert entries[-1].content.value == "line 44"

    def test_unchanged_log_adds_nothing(self) -> None:
        """Reading the same log twice does not duplicate its entries."""

        raw = _log(*_records(0, 40))
        first = translate_state(raw)
        second = translate_state(raw, previous=first)

        assert second[ARLogField.ENTRY_COUNT] == 40

    def test_keeps_entries_the_device_dropped(self) -> None:
        """Entries trimmed from the device buffer stay in the history."""

        first = translate_state(_log(*_records(0, 40)))
        # the device dropped the oldest records and added new ones
        second = translate_state(_log(*_records(20, 60)), previous=first)

        entries = second[ARLogField.ENTRY_LIST]
        assert len(entries) == 60
        assert entries[0].content.value == "line 0"
        assert entries[-1].content.value == "line 59"

    def test_rollover_without_overlap(self) -> None:
        """A buffer sharing nothing with the last read is read whole."""

        first = translate_state(_log(*_records(0, 40)))
        second = translate_state(_log(*_records(500, 540)), previous=first)

        entries = second[ARLogField.ENTRY_LIST]
        assert len(entries) == 80
        assert entries[0].content.value == "line 0"
        assert entries[-1].content.value == "line 539"

    def test_anchor_carried_for_the_next_read(self) -> None:
        """Every read leaves the tail its successor continues from."""

        result = translate_state(_log(*_records(0, 40)))

        anchor = result[ARLogField.ANCHOR]
        # A slice of the log, so classified like any untranslated text
        assert isinstance(anchor, SensitiveText)
        assert str(anchor) != anchor.value
        assert anchor.value.endswith("kernel: line 39")

    def test_previous_ignored_when_unusable(self) -> None:
        """A previous value that is not a log dict is ignored."""

        result = translate_state(_log(*_records(0, 5)), previous="nonsense")

        assert result[ARLogField.ENTRY_COUNT] == 5

    def test_history_limit(self) -> None:
        """The oldest entries drop once the configured limit is passed."""

        ARConfig.set(ARConfKey.LOG_HISTORY_LIMIT, 50)
        try:
            first = translate_state(_log(*_records(0, 40)))
            second = translate_state(_log(*_records(0, 80)), previous=first)
        finally:
            ARConfig.set(ARConfKey.LOG_HISTORY_LIMIT, 50000)

        entries = second[ARLogField.ENTRY_LIST]
        assert len(entries) == 50
        assert entries[0].content.value == "line 30"
        assert entries[-1].content.value == "line 79"

    def test_history_limit_zero_keeps_everything(self) -> None:
        """A limit of zero disables the cap."""

        ARConfig.set(ARConfKey.LOG_HISTORY_LIMIT, 0)
        try:
            first = translate_state(_log(*_records(0, 40)))
            second = translate_state(_log(*_records(0, 80)), previous=first)
        finally:
            ARConfig.set(ARConfKey.LOG_HISTORY_LIMIT, 50000)

        assert second[ARLogField.ENTRY_COUNT] == 80


class TestReplyWithoutText:
    """A reply carrying no log text must not overwrite what is held."""

    @pytest.mark.parametrize("data", ["", '{"nvram_dump-syslog.log":}', None])
    def test_history_and_anchor_survive(self, data: Any) -> None:
        """The entries and the anchor of the previous read are kept."""

        first = translate_state(_log(*_records(0, 40)))

        result = translate_state(data, previous=first)

        assert result[ARLogField.ENTRY_COUNT] == 40
        assert (
            result[ARLogField.ANCHOR].value == first[ARLogField.ANCHOR].value
        )

    @pytest.mark.parametrize("data", ["", '{"nvram_dump-syslog.log":}', None])
    def test_next_read_does_not_duplicate(self, data: Any) -> None:
        """A read after the empty one still continues, never doubles."""

        raw = _log(*_records(0, 40))
        first = translate_state(raw)
        empty = translate_state(data, previous=first)

        third = translate_state(_log(*_records(0, 45)), previous=empty)

        assert third[ARLogField.ENTRY_COUNT] == 45

    def test_without_previous(self) -> None:
        """With nothing held, an empty reply yields the empty log."""

        result = translate_state("")

        assert result[ARLogField.ENTRY_COUNT] == 0
        assert result[ARLogField.ANCHOR].value == ""


class TestSecretRemoval:
    """Taking the values only we know out of the device's own text."""

    @staticmethod
    def _identity() -> ARDeviceIdentity:
        """Build an identity knowing the login name."""

        identity = ARDeviceIdentity()
        identity.update_username(Username("fakeadmin"))
        return identity

    @staticmethod
    def _log() -> str:
        """Build a reply holding the login name as a tag and in a message."""

        return _log(
            "Jul 21 15:08:01 fakeadmin: Server certificate updated.",
            "Jul 21 15:08:02 pppd[21306]: pppd 2.4.7 started by fakeadmin",
        )

    def test_removed_by_default(self) -> None:
        """At the default level the login name reaches no entry."""

        result = translate_state(self._log(), identity=self._identity())

        entries = result[ARLogField.ENTRY_LIST]
        assert len(entries) == 2
        assert not any("fakeadmin" in entry.content.value for entry in entries)
        assert not any("fakeadmin" in entry.content.value for entry in entries)
        # It is a program tag on one of them, not only message text
        assert not any(
            "fakeadmin" in (entry.program_name or "") for entry in entries
        )

    def test_kept_when_unsafe(self) -> None:
        """Asked for raw data, the text is what the device wrote."""

        config = ARInstanceConfig(
            defaults={ARConfKey.SECURITY_LEVEL_DATA: ARSecurityLevel.UNSAFE}
        )

        result = translate_state(
            self._log(), identity=self._identity(), config=config
        )

        entries = result[ARLogField.ENTRY_LIST]
        assert entries[0].program_name == "fakeadmin"
        assert "fakeadmin" in entries[1].content.value

    def test_without_an_identity(self) -> None:
        """Not knowing the name, there is nothing to search the text for."""

        result = translate_state(self._log())

        assert len(result[ARLogField.ENTRY_LIST]) == 2

    def test_without_a_username(self) -> None:
        """An identity that never learned the name changes nothing."""

        result = translate_state(self._log(), identity=ARDeviceIdentity())

        assert len(result[ARLogField.ENTRY_LIST]) == 2

    def test_anchor_matches_the_cleaned_text(self) -> None:
        """The anchor is cleaned too, so the next read still continues."""

        identity = self._identity()
        first = translate_state(self._log(), identity=identity)

        grown = _log(
            "Jul 21 15:08:01 fakeadmin: Server certificate updated.",
            "Jul 21 15:08:02 pppd[21306]: pppd 2.4.7 started by fakeadmin",
            "Jul 21 15:08:03 ntp: start NTP update",
        )
        second = translate_state(grown, identity=identity, previous=first)

        # Continued, not read whole again: three entries, not five
        assert second[ARLogField.ENTRY_COUNT] == 3

    def test_device_mac_removed(self) -> None:
        """The device's own MAC is a value we know, so it is cleaned too."""

        identity = ARDeviceIdentity()
        identity._mac = MacAddress("C8:7F:54:00:00:01")
        config = ARInstanceConfig(
            defaults={ARConfKey.SECURITY_LEVEL_DATA: ARSecurityLevel.STRICT}
        )
        # The device spells it upper case, the identity holds it lower
        raw = _log(
            "Jul 21 15:08:01 init: fwver: 3.0.0.6 (/ha:C8:7F:54:00:00:01 )"
        )

        result = translate_state(raw, identity=identity, config=config)

        content = result[ARLogField.ENTRY_LIST][0].content.value
        assert "C8:7F:54:00:00:01" not in content
        assert "c8:7f:54:00:00:01" not in content

    def test_serial_removed(self) -> None:
        """The serial rides in the same banner and is cleaned with it."""

        identity = ARDeviceIdentity()
        identity._serial = "R2FAKE000000ABC"
        config = ARInstanceConfig(
            defaults={ARConfKey.SECURITY_LEVEL_DATA: ARSecurityLevel.STRICT}
        )
        raw = _log(
            "Jul 21 15:08:01 init: fwver: 3.0.0.6 (sn:R2FAKE000000ABC )"
        )

        result = translate_state(raw, identity=identity, config=config)

        assert (
            "R2FAKE000000ABC"
            not in result[ARLogField.ENTRY_LIST][0].content.value
        )


class TestYearAnchor:
    """The year a stamp does not carry comes from the device."""

    def test_device_year_is_used(self) -> None:
        """The device's own clock decides the year, not the host's."""

        identity = ARDeviceIdentity()
        identity.update_device_time(
            datetime(2019, 7, 31, 10, 24, 4, tzinfo=UTC)
        )

        result = translate_state(
            _log("Jul 21 15:08:01 kernel: boot"), identity=identity
        )

        assert result[ARLogField.ENTRY_LIST][0].timestamp.year == 2019

    def test_device_offset_is_used(self) -> None:
        """A stamp is placed in the zone the device wrote it in."""

        cest = timezone(timedelta(hours=2))
        identity = ARDeviceIdentity()
        identity.update_device_time(
            datetime(2026, 7, 31, 10, 24, 4, tzinfo=cest)
        )

        result = translate_state(
            _log("Jul 21 15:08:01 kernel: boot"), identity=identity
        )

        assert result[ARLogField.ENTRY_LIST][0].timestamp == datetime(
            2026, 7, 21, 15, 8, 1, tzinfo=cest
        )

    def test_host_offset_without_a_device_clock(self) -> None:
        """With no device clock the host's offset stands in, never none."""

        result = translate_state(_log("Jul 21 15:08:01 kernel: boot"))

        timestamp = result[ARLogField.ENTRY_LIST][0].timestamp
        assert timestamp.tzinfo is not None
        assert timestamp.utcoffset() == datetime.now().astimezone().utcoffset()

    def test_host_year_without_a_device_clock(self) -> None:
        """With no device clock the host's year is the only anchor."""

        result = translate_state(_log("Jul 21 15:08:01 kernel: boot"))

        entry = result[ARLogField.ENTRY_LIST][0]
        assert entry.timestamp.year == datetime.now(UTC).year
