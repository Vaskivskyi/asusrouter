"""Tests for the entry-tier log query helpers."""

from __future__ import annotations

from datetime import datetime

import pytest

from asusrouter.modules.log.entry import (
    ARLogEntry,
    ARLogProgram,
    ARLogProgramGroup,
)
from asusrouter.modules.log.enums import ARLogField, ARProgram
from asusrouter.modules.log.query.entries import (
    group_programs,
    last_entries,
    summarize,
    unique_entries,
)
from asusrouter.modules.log.query.event import ARLogEvent
from asusrouter.modules.log.translate.ntp import AREventNtp
from asusrouter.tools.security.text import SensitiveText

_ENTRIES = [
    ARLogEntry(
        f"Jul 21 15:08:0{index}", content=SensitiveText(f"line {index}")
    )
    for index in range(5)
]

_MIXED = [
    ARLogEntry(
        "Jul 21 15:08:01",
        program=ARLogProgram("vpnclient5", 10),
        content=SensitiveText("up"),
        timestamp=datetime(2026, 7, 21, 15, 8, 1),
    ),
    ARLogEntry(
        "Jul 21 15:08:05",
        program=ARLogProgram("wlceventd"),
        content=SensitiveText("Deauth WL0"),
        timestamp=datetime(2026, 7, 21, 15, 8, 5),
    ),
    ARLogEntry(
        "Jul 21 15:08:09",
        program=ARLogProgram("vpnclient6", 22),
        content=SensitiveText("up again"),
        timestamp=datetime(2026, 7, 21, 15, 8, 9),
    ),
    ARLogEntry("Jul 21 15:08:11", content=SensitiveText("no program here")),
]


_EVENTS = [
    ARLogEvent(
        timestamp=entry.timestamp,
        program=ARProgram.NTP,
        program_name="ntp",
        event_type=AREventNtp.START_UPDATE,
        raw=entry.content.value,
    )
    for entry in _MIXED[:2]
]


class TestLastEntries:
    """Slicing the last items off a list."""

    def test_all_when_none(self) -> None:
        """No count returns the very same list, uncopied."""

        assert last_entries(_ENTRIES) is _ENTRIES

    def test_last_n(self) -> None:
        """A count returns only the final items, order kept."""

        result = last_entries(_ENTRIES, 2)

        assert result == _ENTRIES[-2:]

    def test_count_exceeds_length(self) -> None:
        """A count past the length returns everything."""

        assert last_entries(_ENTRIES, 99) == _ENTRIES

    @pytest.mark.parametrize("count", [0, -3])
    def test_non_positive(self, count: int) -> None:
        """Zero or negative count returns nothing."""

        assert last_entries(_ENTRIES, count) == []

    def test_generic_over_tuples(self) -> None:
        """The slice works on any list, not only entries."""

        assert last_entries([(1, "a"), (2, "b"), (3, "c")], 1) == [(3, "c")]


class TestSummarize:
    """Building the on-demand data dict."""

    def test_entry_list_default(self) -> None:
        """Without events the dict carries raw entries and their count."""

        result = summarize(_MIXED, total=4)

        assert result[ARLogField.ENTRY_LIST] is _MIXED
        assert ARLogField.EVENT_LIST not in result
        assert result[ARLogField.ENTRY_COUNT] == len(_MIXED)
        assert result[ARLogField.LAST_ENTRY] is None  # last entry has no time

    def test_programs_opt_in(self) -> None:
        """`programs=True` adds the program grouping."""

        result = summarize(_MIXED, total=4, programs=True)

        assert result[ARLogField.PROGRAM_LIST] == group_programs(_MIXED)

    def test_programs_default_skips_grouping(self) -> None:
        """Grouping is off by default (the costly path)."""

        assert ARLogField.PROGRAM_LIST not in summarize(_MIXED, total=4)

    def test_events_swap_list_key(self) -> None:
        """`events` replaces `ENTRY_LIST` with `EVENT_LIST`."""

        result = summarize(_MIXED[:2], total=4, events=_EVENTS)

        assert result[ARLogField.EVENT_LIST] is _EVENTS
        assert ARLogField.ENTRY_LIST not in result

    def test_events_drive_count_and_last(self) -> None:
        """With events the count and last entry come from them, not entries."""

        result = summarize([], total=9, events=_EVENTS)

        assert result[ARLogField.ENTRY_COUNT] == len(_EVENTS)
        assert result[ARLogField.LAST_ENTRY] == _EVENTS[-1].timestamp

    def test_total_when_given(self) -> None:
        """`total` surfaces the pre-filter count under `TOTAL`."""

        result = summarize(_MIXED[:1], total=42)

        assert result[ARLogField.TOTAL] == 42

    def test_total_always_reported(self) -> None:
        """`TOTAL` is part of every dict, filtered or not."""

        assert summarize(_MIXED, total=len(_MIXED))[ARLogField.TOTAL] == len(
            _MIXED
        )

    def test_last_entry_timestamp(self) -> None:
        """Last entry mirrors the newest entry's resolved timestamp."""

        result = summarize(_MIXED[:2], total=4)

        assert result[ARLogField.LAST_ENTRY] == _MIXED[1].timestamp

    def test_empty(self) -> None:
        """An empty list summarises to zeros and no last entry."""

        result = summarize([], total=0, programs=True)

        assert result[ARLogField.ENTRY_COUNT] == 0
        assert result[ARLogField.LAST_ENTRY] is None
        assert result[ARLogField.PROGRAM_LIST] == []


class TestGroupPrograms:
    """Grouping programs by name with their pids and standard kind."""

    def test_grouped_with_kind_and_index(self) -> None:
        """Each group carries its raw name, standard kind and index."""

        result = group_programs(_MIXED)

        assert result == [
            ARLogProgramGroup(
                name="vpnclient5",
                program=ARProgram.VPN_CLIENT,
                index=5,
                pids=(10,),
                pidless=False,
                count=1,
            ),
            ARLogProgramGroup(
                name="wlceventd",
                program=ARProgram.WIRELESS_CLIENT_DAEMON,
                index=None,
                pids=(),
                pidless=True,
                count=1,
            ),
            ARLogProgramGroup(
                name="vpnclient6",
                program=ARProgram.VPN_CLIENT,
                index=6,
                pids=(22,),
                pidless=False,
                count=1,
            ),
        ]

    def test_mixed_pid_and_pidless(self) -> None:
        """A name seen with and without a pid keeps ints and flags pidless."""

        entries = [
            ARLogEntry(
                "Jul 21 15:08:01",
                program=ARLogProgram("ntp", 7),
            ),
            ARLogEntry(
                "Jul 21 15:08:02", "ntp: b", program=ARLogProgram("ntp")
            ),
        ]

        assert group_programs(entries) == [
            ARLogProgramGroup(
                name="ntp",
                program=ARProgram.NTP,
                pids=(7,),
                pidless=True,
                count=2,
            )
        ]

    def test_parsed_unknown_for_unrecognized(self) -> None:
        """An unknown name still groups, program UNKNOWN, no index."""

        entries = [
            ARLogEntry(
                "Jul 21 15:08:01", "ARK: x", program=ARLogProgram("ARK")
            )
        ]

        group = group_programs(entries)[0]
        assert group.program is ARProgram.UNKNOWN
        assert group.index is None

    def test_skips_programless(self) -> None:
        """Entries without a program are ignored."""

        entries = [ARLogEntry("Jul 21 15:08:01", "bare line")]

        assert group_programs(entries) == []


class TestUniqueEntries:
    """Deduplicating entries by content, ignoring the timestamp."""

    def test_dedup_keeps_first(self) -> None:
        """Repeated content is dropped, the first occurrence is kept."""

        entries = [
            ARLogEntry(
                "Jul 21 15:08:01", "kernel: a", content=SensitiveText("a")
            ),
            ARLogEntry(
                "Jul 21 15:09:02", "kernel: a", content=SensitiveText("a")
            ),
            ARLogEntry(
                "Jul 21 15:10:03", "kernel: b", content=SensitiveText("b")
            ),
        ]

        result = unique_entries(entries)

        assert [entry.content.value for entry in result] == ["a", "b"]
        assert result[0].timestamp_str == "Jul 21 15:08:01"

    def test_empty(self) -> None:
        """An empty list yields an empty list."""

        assert unique_entries([]) == []
