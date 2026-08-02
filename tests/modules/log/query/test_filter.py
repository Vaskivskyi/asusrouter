"""Tests for the unified log filtering interface."""

from __future__ import annotations

import pytest

from asusrouter.modules.log.clock import resolve_datetimes
from asusrouter.modules.log.entry import ARLogEntry
from asusrouter.modules.log.enums import AREventKey, ARLogField, ARProgram
from asusrouter.modules.log.parser import parse_log
from asusrouter.modules.log.query import filter as filter_module
from asusrouter.modules.log.query.event import ARLogEvent, build_event
from asusrouter.modules.log.query.filter import filter_log
from asusrouter.modules.log.query.predicate import ARLogContains, ARLogMatch

_RAW = (
    "Jul 22 08:43:21 ntp: start NTP update\n"
    "Jul 22 08:43:22 rc_service: cfg 1:notify_rc restart_wan\n"
    "Jul 22 08:43:23 ntp: start NTP update\n"
    "Jul 22 08:43:24 kernel: boot\n"
)
_ENTRIES = resolve_datetimes(parse_log(_RAW))

_NTP = ARLogMatch(AREventKey.PROGRAM, ARProgram.NTP)


class TestNoPredicate:
    """The cheap path: raw entries, no translation."""

    def test_entry_list_and_total(self) -> None:
        """Every entry is returned raw, with the pre-filter total."""

        result = filter_log(_ENTRIES)

        assert len(result[ARLogField.ENTRY_LIST]) == 4
        assert result[ARLogField.ENTRY_COUNT] == 4
        assert result[ARLogField.TOTAL] == 4
        assert ARLogField.EVENT_LIST not in result

    def test_last_slices_before_anything(self) -> None:
        """`last` keeps only the final entries, total stays full."""

        result = filter_log(_ENTRIES, last=1)

        entries = result[ARLogField.ENTRY_LIST]
        assert len(entries) == 1
        assert entries[0].content.value == "boot"
        assert result[ARLogField.TOTAL] == 4

    def test_unique_dedups_content(self) -> None:
        """`unique` collapses the repeated NTP line, total stays full."""

        result = filter_log(_ENTRIES, unique=True)

        assert result[ARLogField.ENTRY_COUNT] == 3
        assert result[ARLogField.TOTAL] == 4

    def test_programs_opt_in(self) -> None:
        """`programs=True` adds the program grouping."""

        assert ARLogField.PROGRAM_LIST in filter_log(_ENTRIES, programs=True)

    def test_programs_grouped_over_matches_only(self) -> None:
        """With a predicate the grouping covers the survivors, not the log."""

        result = filter_log(_ENTRIES, predicate=_NTP, programs=True)

        groups = result[ARLogField.PROGRAM_LIST]
        assert [group.name for group in groups] == ["ntp"]
        assert groups[0].count == 2

    def test_empty(self) -> None:
        """No entries yields an empty, zeroed dict."""

        result = filter_log([])

        assert result[ARLogField.ENTRY_LIST] == []
        assert result[ARLogField.ENTRY_COUNT] == 0
        assert result[ARLogField.TOTAL] == 0
        assert result[ARLogField.LAST_ENTRY] is None


class TestWithPredicate:
    """The rich path: translated, filtered events."""

    def test_event_list_filtered(self) -> None:
        """A predicate translates survivors into `EVENT_LIST`."""

        result = filter_log(_ENTRIES, predicate=_NTP)

        events = result[ARLogField.EVENT_LIST]
        assert len(events) == 2
        assert all(event.program is ARProgram.NTP for event in events)
        assert result[ARLogField.ENTRY_COUNT] == 2
        assert result[ARLogField.TOTAL] == 4
        assert ARLogField.ENTRY_LIST not in result

    def test_content_predicate(self) -> None:
        """A `ARLogContains` predicate matches on the raw text."""

        result = filter_log(_ENTRIES, predicate=ARLogContains("restart_wan"))

        events = result[ARLogField.EVENT_LIST]
        assert len(events) == 1
        assert events[0].program is ARProgram.RC_SERVICE

    def test_last_slices_after_filter(self) -> None:
        """`last` trims the matched events, not the raw log."""

        result = filter_log(_ENTRIES, predicate=_NTP, last=1)

        assert len(result[ARLogField.EVENT_LIST]) == 1
        assert result[ARLogField.ENTRY_COUNT] == 1
        assert result[ARLogField.TOTAL] == 4

    def test_unique_before_filter(self) -> None:
        """`unique` runs before translation, then the predicate filters."""

        result = filter_log(_ENTRIES, predicate=_NTP, unique=True)

        assert len(result[ARLogField.EVENT_LIST]) == 1

    def test_last_entry_resolved(self) -> None:
        """The survivors carry a resolved timestamp under `LAST_ENTRY`."""

        result = filter_log(_ENTRIES, predicate=_NTP)

        assert result[ARLogField.LAST_ENTRY] is not None

    def test_predicate_without_prescreen(self) -> None:
        """A predicate judging only events still filters every entry."""

        class OnlyMatches:
            """A predicate offering no prescreen."""

            def matches(self, event: ARLogEvent) -> bool:
                """Keep the NTP events."""

                return event.program is ARProgram.NTP

        result = filter_log(_ENTRIES, predicate=OnlyMatches())

        assert len(result[ARLogField.EVENT_LIST]) == 2

    def test_prescreen_skips_translation(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A prescreened-out entry is never translated."""

        translated: list[str] = []

        def _spy(entry: ARLogEntry) -> ARLogEvent:
            """Record the entry, then translate it."""

            translated.append(entry.content.value)
            return build_event(entry)

        monkeypatch.setattr(filter_module, "build_event", _spy)
        filter_log(_ENTRIES, predicate=_NTP)

        assert translated == ["start NTP update"] * 2
