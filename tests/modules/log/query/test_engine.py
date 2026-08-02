"""Tests for the find/group query engine."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.common.command import ARService
from asusrouter.modules.log.enums import AREventKey, ARProgram
from asusrouter.modules.log.query.engine import find, group
from asusrouter.modules.log.query.event import ARLogEvent
from asusrouter.modules.log.query.predicate import ARLogMatch
from asusrouter.modules.log.translate.ntp import AREventNtp


def _event(program: ARProgram, data: Any = None) -> ARLogEvent:
    """Build an envelope with a program and event data."""

    return ARLogEvent(
        timestamp=None,
        program=program,
        program_name=program.value,
        event_type=AREventNtp.START_UPDATE,
        raw="",
        data=data if data is not None else {},
    )


_WAN = ARService.WAN_RESTART
_FW = ARService.FIREWALL_RESTART


class TestFind:
    """Filtering events by a predicate."""

    def test_filters_and_preserves_order(self) -> None:
        """Matching events are returned in their original order."""

        events = [
            _event(ARProgram.NTP),
            _event(ARProgram.KERNEL),
            _event(ARProgram.NTP),
        ]

        result = find(events, ARLogMatch(AREventKey.PROGRAM, "ntp"))

        assert result == [events[0], events[2]]

    def test_no_match(self) -> None:
        """A predicate matching nothing yields an empty list."""

        events = [_event(ARProgram.NTP)]

        assert find(events, ARLogMatch(AREventKey.PROGRAM, "kernel")) == []


class TestGroup:
    """Partitioning events by a dimension."""

    def test_by_program(self) -> None:
        """Events bucket by their program value."""

        events = [
            _event(ARProgram.NTP),
            _event(ARProgram.KERNEL),
            _event(ARProgram.NTP),
        ]

        result = group(events, AREventKey.PROGRAM)

        assert result == {
            ARProgram.NTP: [events[0], events[2]],
            ARProgram.KERNEL: [events[1]],
        }

    def test_multi_valued_repeats(self) -> None:
        """An event with several axis values lands in each bucket."""

        both = _event(ARProgram.RC_SERVICE, {AREventKey.SERVICES: (_WAN, _FW)})
        one = _event(ARProgram.RC_SERVICE, {AREventKey.SERVICE: _FW})

        result = group([both, one], AREventKey.SERVICE)

        assert result == {
            ARService.WAN_RESTART: [both],
            ARService.FIREWALL_RESTART: [both, one],
        }

    def test_missing_axis_omitted(self) -> None:
        """Events lacking the axis do not appear in any bucket."""

        assert group([_event(ARProgram.NTP)], AREventKey.SERVICE) == {}
