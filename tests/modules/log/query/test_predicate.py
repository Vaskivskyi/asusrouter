"""Tests for log event query predicates."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from typing import Any as AnyType

import pytest

from asusrouter.modules.log.entry import ARLogEntry, ARLogProgram
from asusrouter.modules.log.enums import AREventKey, ARProgram
from asusrouter.modules.log.query.event import ARLogEvent
from asusrouter.modules.log.query.predicate import (
    ARLogAll,
    ARLogAny,
    ARLogBetween,
    ARLogContains,
    ARLogEverything,
    ARLogMatch,
    ARLogNot,
    may_match,
)
from asusrouter.modules.log.translate.ntp import AREventNtp
from asusrouter.tools.identifiers import MacAddress
from asusrouter.tools.security.text import SensitiveText

_MAC = MacAddress("aa:bb:cc:00:00:01")
_WHEN = datetime(2026, 7, 22, 8, 43, 21)


def _event(**overrides: AnyType) -> ARLogEvent:
    """Build an envelope with sensible defaults."""

    base: dict[str, AnyType] = {
        "timestamp": _WHEN,
        "program": ARProgram.NTP,
        "program_name": "ntp",
        "event_type": AREventNtp.START_UPDATE,
        "raw": "start NTP update",
        "data": {AREventKey.CLIENT_MAC: _MAC},
    }
    base.update(overrides)

    return ARLogEvent(**base)


def _entry(**overrides: AnyType) -> ARLogEntry:
    """Build the untranslated entry the default event comes from."""

    base: dict[str, AnyType] = {
        "timestamp_str": "Jul 22 08:43:21",
        "timestamp": _WHEN,
        "program": ARLogProgram(name="ntp"),
        "content": SensitiveText("start NTP update"),
    }
    base.update(overrides)

    return ARLogEntry(**base)


class TestMatch:
    """Equality on a query dimension."""

    def test_facet_hit_cross_format(self) -> None:
        """A differently-formatted MAC still matches the facet."""

        assert ARLogMatch(AREventKey.CLIENT_MAC, "aa-bb-cc-00-00-01").matches(
            _event()
        )

    def test_facet_miss(self) -> None:
        """A different MAC does not match."""

        assert not ARLogMatch(
            AREventKey.CLIENT_MAC, "ff:ff:ff:ff:ff:ff"
        ).matches(_event())

    def test_program_dimension(self) -> None:
        """A program name matches the envelope program."""

        assert ARLogMatch(AREventKey.PROGRAM, "ntp").matches(_event())

    def test_event_type_via_string(self) -> None:
        """A raw event-type string matches through StrEnum equality."""

        assert ARLogMatch(AREventKey.EVENT_TYPE, "start_update").matches(
            _event()
        )


class TestBetween:
    """Inclusive timestamp window."""

    def test_inside(self) -> None:
        """A timestamp inside the window matches."""

        window = ARLogBetween(
            after=datetime(2026, 7, 22, 8, 0),
            before=datetime(2026, 7, 22, 9, 0),
        )

        assert window.matches(_event())

    def test_before_only(self) -> None:
        """An open lower bound still matches within the upper bound."""

        assert ARLogBetween(before=_WHEN).matches(_event())

    def test_after_excludes(self) -> None:
        """A timestamp before the lower bound is excluded."""

        assert not ARLogBetween(after=datetime(2026, 7, 22, 9, 0)).matches(
            _event()
        )

    def test_no_timestamp(self) -> None:
        """An event with no timestamp never matches a window."""

        assert not ARLogBetween(before=_WHEN).matches(_event(timestamp=None))

    def test_aware_bound_against_aware_stamp(self) -> None:
        """A device that stated its offset is compared in that offset."""

        cest = timezone(timedelta(hours=2))
        event = _event(timestamp=_WHEN.replace(tzinfo=cest))
        window = ARLogBetween(
            after=datetime(2026, 7, 22, 8, 0, tzinfo=cest),
            before=datetime(2026, 7, 22, 9, 0, tzinfo=cest),
        )

        assert window.matches(event)

    @pytest.mark.parametrize(
        ("stamp_tz", "bound_tz"),
        [(timezone(timedelta(hours=2)), None), (None, UTC)],
        ids=["aware_stamp_naive_bound", "naive_stamp_aware_bound"],
    )
    def test_mismatched_awareness_reads_as_wall_clock(
        self, stamp_tz: timezone | None, bound_tz: timezone | None
    ) -> None:
        """A bound that disagrees on the offset is read, not refused."""

        event = _event(timestamp=_WHEN.replace(tzinfo=stamp_tz))
        window = ARLogBetween(
            after=datetime(2026, 7, 22, 8, 0, tzinfo=bound_tz),
            before=datetime(2026, 7, 22, 9, 0, tzinfo=bound_tz),
        )

        assert window.matches(event)


class TestContains:
    """Case-folded raw substring."""

    def test_hit(self) -> None:
        """A case-insensitive substring matches the raw content."""

        assert ARLogContains("ntp UPDATE".upper()).matches(
            _event(raw="start NTP update")
        )

    def test_miss(self) -> None:
        """A missing substring does not match."""

        assert not ARLogContains("reboot").matches(_event())

    def test_text_folded_once(self) -> None:
        """The query text is case-folded on construction, not per event."""

        assert ARLogContains("NTP Update").text == "ntp update"


class TestCombinators:
    """AND / OR / NOT composition."""

    def test_all_true(self) -> None:
        """ARLogAll requires every sub-predicate to match."""

        predicate = ARLogAll(
            ARLogMatch(AREventKey.PROGRAM, "ntp"),
            ARLogMatch(AREventKey.CLIENT_MAC, _MAC),
        )

        assert predicate.matches(_event())

    def test_all_one_fails(self) -> None:
        """ARLogAll fails when any sub-predicate fails."""

        predicate = ARLogAll(
            ARLogMatch(AREventKey.PROGRAM, "ntp"),
            ARLogMatch(AREventKey.PROGRAM, "kernel"),
        )

        assert not predicate.matches(_event())

    def test_any_one_matches(self) -> None:
        """ARLogAny matches when at least one sub-predicate matches."""

        predicate = ARLogAny(
            ARLogMatch(AREventKey.PROGRAM, "kernel"),
            ARLogMatch(AREventKey.PROGRAM, "ntp"),
        )

        assert predicate.matches(_event())

    def test_any_none(self) -> None:
        """ARLogAny fails when no sub-predicate matches."""

        assert not ARLogAny(ARLogMatch(AREventKey.PROGRAM, "kernel")).matches(
            _event()
        )

    def test_not_inverts(self) -> None:
        """ARLogNot inverts the wrapped predicate."""

        assert ARLogNot(ARLogMatch(AREventKey.PROGRAM, "kernel")).matches(
            _event()
        )


class TestPrescreen:
    """Rejecting an entry before it is translated."""

    def test_may_match_without_prescreen(self) -> None:
        """A predicate not offering a prescreen keeps every entry."""

        assert may_match(ARLogNot(ARLogContains("x")), _entry()) is True

    def test_match_on_program(self) -> None:
        """PROGRAM is decided on the entry's own tag."""

        assert ARLogMatch(AREventKey.PROGRAM, "ntp").prescreen(_entry())
        assert not ARLogMatch(AREventKey.PROGRAM, "kernel").prescreen(_entry())

    def test_match_on_program_name(self) -> None:
        """PROGRAM_NAME is decided on the entry's raw tag."""

        assert ARLogMatch(AREventKey.PROGRAM_NAME, "ntp").prescreen(_entry())

    def test_match_on_translated_dimension_keeps_entry(self) -> None:
        """A dimension only known after translation cannot reject."""

        assert ARLogMatch(AREventKey.CLIENT_MAC, _MAC).prescreen(_entry())

    def test_between_uses_entry_timestamp(self) -> None:
        """The window is decided on the entry's own timestamp."""

        assert ARLogBetween(before=_WHEN).prescreen(_entry())
        assert not ARLogBetween(after=datetime(2026, 7, 22, 9, 0)).prescreen(
            _entry()
        )

    def test_contains_uses_entry_content(self) -> None:
        """The substring is decided on the entry's content."""

        assert ARLogContains("NTP").prescreen(_entry())
        assert not ARLogContains("reboot").prescreen(_entry())

    def test_all_requires_every_sub(self) -> None:
        """ARLogAll rejects when any sub-predicate rejects."""

        assert ARLogAll(
            ARLogMatch(AREventKey.PROGRAM, "ntp"), ARLogContains("ntp")
        ).prescreen(_entry())
        assert not ARLogAll(
            ARLogMatch(AREventKey.PROGRAM, "ntp"), ARLogContains("reboot")
        ).prescreen(_entry())

    def test_any_requires_one_sub(self) -> None:
        """ARLogAny keeps the entry when one sub-predicate keeps it."""

        assert ARLogAny(
            ARLogMatch(AREventKey.PROGRAM, "kernel"), ARLogContains("ntp")
        ).prescreen(_entry())
        assert not ARLogAny(
            ARLogMatch(AREventKey.PROGRAM, "kernel"), ARLogContains("reboot")
        ).prescreen(_entry())


class TestEverything:
    """The unfiltered predicate."""

    def test_matches_any_event(self) -> None:
        """Every event matches, whatever it carries."""

        assert ARLogEverything().matches(_event())
        assert ARLogEverything().matches(_event(timestamp=None, data={}))

    def test_prescreens_any_entry(self) -> None:
        """Every entry stays in play, so nothing is skipped."""

        assert ARLogEverything().prescreen(_entry())
        assert may_match(ARLogEverything(), _entry()) is True
