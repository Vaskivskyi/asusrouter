"""Tests for the declarative message pattern engine."""

from __future__ import annotations

from enum import StrEnum

import pytest

from asusrouter.modules.log.enums import AREventKey
from asusrouter.modules.log.translate.common import MAC_PATTERN
from asusrouter.modules.log.translate.pattern import (
    ARLogPattern,
    ARLogPatternSet,
)
from asusrouter.tools.identifiers import Hostname, MacAddress, Username
from tests.modules.log.translate import classified, unread

_KEY = AREventKey


class _Event(StrEnum):
    """Minimal event enum for the engine tests."""

    UNKNOWN = "unknown"

    HIT = "hit"
    OTHER = "other"


class TestRead:
    """Reading one event out of a message."""

    def test_fields_named_after_keys(self) -> None:
        """Every group fills the event key it is named after."""

        pattern = ARLogPattern(
            _Event.HIT, r"port (?P<port>\d+) on (?P<chain>\w+)"
        )

        assert pattern.read("port 80 on FORWARD", _Event.UNKNOWN) == {
            _KEY.EVENT_TYPE: _Event.HIT,
            _KEY.RAW: "port 80 on FORWARD",
            _KEY.PORT: "80",
            _KEY.CHAIN: "FORWARD",
        }

    def test_converter_applied(self) -> None:
        """A converter shapes the value of its key."""

        pattern = ARLogPattern(
            _Event.HIT, r"port (?P<port>\d+)", convert={_KEY.PORT: int}
        )

        assert pattern.read("port 80", _Event.UNKNOWN)[_KEY.PORT] == 80

    def test_no_match(self) -> None:
        """A message the pattern does not match yields None."""

        pattern = ARLogPattern(_Event.HIT, r"port (?P<port>\d+)")

        assert pattern.read("nothing here", _Event.UNKNOWN) is None

    def test_absent_group_omitted(self) -> None:
        """An optional group that did not take part leaves its key out."""

        pattern = ARLogPattern(
            _Event.HIT,
            r"link(?: at (?P<speed>\d+))?",
            convert={_KEY.SPEED: int},
        )

        assert _KEY.SPEED not in pattern.read("link", _Event.UNKNOWN)

    def test_converter_none_omitted(self) -> None:
        """A converter returning None leaves its key out."""

        pattern = ARLogPattern(
            _Event.HIT,
            r"speed (?P<speed>\w+)",
            convert={_KEY.SPEED: lambda _value: None},
        )

        assert _KEY.SPEED not in pattern.read("speed fast", _Event.UNKNOWN)


class TestEventType:
    """Picking the event type."""

    def test_mapped_by_group(self) -> None:
        """The `event_type` group picks the member, staying out of the data."""

        pattern = ARLogPattern(
            {"up": _Event.HIT, "down": _Event.OTHER},
            r"link (?P<event_type>up|down)",
        )

        assert pattern.read("link down", _Event.UNKNOWN) == {
            _KEY.EVENT_TYPE: _Event.OTHER,
            _KEY.RAW: "link down",
        }

    def test_unmapped_value_falls_back(self) -> None:
        """An unmapped group value yields the caller's UNKNOWN member."""

        pattern = ARLogPattern({"up": _Event.HIT}, r"link (?P<event_type>\w+)")

        assert (
            pattern.read("link sideways", _Event.UNKNOWN)[_KEY.EVENT_TYPE]
            is _Event.UNKNOWN
        )


class TestDerive:
    """Filling a key out of another key's value."""

    def test_derived_from_read_key(self) -> None:
        """The derived key is built from the value already read."""

        pattern = ARLogPattern(
            _Event.HIT,
            r"port (?P<port>\d+)",
            convert={_KEY.PORT: int},
            derive={_KEY.VALUE: (_KEY.PORT, lambda port: port * 2)},
        )

        assert pattern.read("port 21", _Event.UNKNOWN)[_KEY.VALUE] == 42

    def test_absent_source_skips(self) -> None:
        """A source key the message did not fill derives nothing."""

        pattern = ARLogPattern(
            _Event.HIT,
            r"link(?: at (?P<speed>\d+))?",
            derive={_KEY.VALUE: (_KEY.SPEED, str.strip)},
        )

        assert _KEY.VALUE not in pattern.read("link", _Event.UNKNOWN)


class TestMarker:
    """The literal gate skipping the regex."""

    def test_missing_marker_skips(self) -> None:
        """A message without the marker never matches."""

        pattern = ARLogPattern(_Event.HIT, r"(?P<port>\d+)", marker="port")

        assert pattern.read("80", _Event.UNKNOWN) is None
        assert pattern.read("port 80", _Event.UNKNOWN) is not None


class TestPlanValidation:
    """Rejecting a broken plan when the pattern is built."""

    def test_group_without_key(self) -> None:
        """A group named after no event key is rejected."""

        with pytest.raises(ValueError, match="without an event key"):
            ARLogPattern(_Event.HIT, r"(?P<not_a_key>\d+)")

    def test_unused_converter(self) -> None:
        """A converter for a key the pattern never reads is rejected."""

        with pytest.raises(ValueError, match="never reads"):
            ARLogPattern(
                _Event.HIT, r"(?P<port>\d+)", convert={_KEY.CHAIN: str.strip}
            )

    def test_derive_from_unread_key(self) -> None:
        """Deriving from a key the pattern never reads is rejected."""

        with pytest.raises(ValueError, match="never reads"):
            ARLogPattern(
                _Event.HIT,
                r"(?P<port>\d+)",
                derive={_KEY.VALUE: (_KEY.CHAIN, str.strip)},
            )


class TestRawClassification:
    """Deciding the level a matched message's raw text is exposed at."""

    def test_no_sensitive_field_stays_plain(self) -> None:
        """A shape read in full needs no protection of its own."""

        pattern = ARLogPattern(_Event.HIT, r"port (?P<port>\d+)")

        assert pattern.read("port 80", _Event.UNKNOWN)[_KEY.RAW] == "port 80"

    def test_untyped_converter_stays_plain(self) -> None:
        """A converter building no sensitive type does not classify."""

        pattern = ARLogPattern(
            _Event.HIT, r"port (?P<port>\d+)", convert={_KEY.PORT: int}
        )

        assert pattern.read("port 80", _Event.UNKNOWN)[_KEY.RAW] == "port 80"

    def test_sensitive_field_classifies_raw(self) -> None:
        """A sensitive field exposes the message from its own level."""

        pattern = ARLogPattern(
            _Event.HIT,
            rf"sta (?P<client_mac>{MAC_PATTERN})",
            convert={_KEY.CLIENT_MAC: MacAddress.from_value_safe},
        )
        content = "sta AA:BB:CC:00:00:01"

        assert pattern.read(content, _Event.UNKNOWN)[_KEY.RAW] == (
            classified(content, MacAddress.reveal_level)
        )

    def test_strictest_field_wins(self) -> None:
        """Several sensitive fields expose the raw at the strictest level."""

        pattern = ARLogPattern(
            _Event.HIT,
            r"(?P<hostname>\w+) as (?P<subject>\w+)",
            convert={
                _KEY.HOSTNAME: Hostname.from_value_safe,
                _KEY.SUBJECT: Username.from_value_safe,
            },
        )
        content = "myhost as someone"

        # A hostname reveals at REASONABLE, a login name only at UNSAFE
        assert pattern.read(content, _Event.UNKNOWN)[_KEY.RAW] == (
            classified(content, Username.reveal_level)
        )

    def test_planned_field_counts_when_absent(self) -> None:
        """An optional group that did not match still classifies the shape."""

        pattern = ARLogPattern(
            _Event.HIT,
            rf"link(?: (?P<client_mac>{MAC_PATTERN}))?",
            convert={_KEY.CLIENT_MAC: MacAddress.from_value_safe},
        )
        event = pattern.read("link", _Event.UNKNOWN)

        assert _KEY.CLIENT_MAC not in event
        assert event[_KEY.RAW] == classified("link", MacAddress.reveal_level)

    def test_derived_field_counts(self) -> None:
        """A key derived into a sensitive type classifies the raw as well."""

        pattern = ARLogPattern(
            _Event.HIT,
            r"sta (?P<value>\S+)",
            derive={_KEY.CLIENT_MAC: (_KEY.VALUE, MacAddress.from_value_safe)},
        )
        content = "sta AA:BB:CC:00:00:01"

        assert pattern.read(content, _Event.UNKNOWN)[_KEY.RAW] == (
            classified(content, MacAddress.reveal_level)
        )


class TestPatternSet:
    """First-match-else-unknown dispatch over a program's patterns."""

    def test_first_match_wins(self) -> None:
        """The first matching pattern's event is returned."""

        patterns = ARLogPatternSet(
            _Event.UNKNOWN,
            (
                ARLogPattern(_Event.OTHER, r"never"),
                ARLogPattern(_Event.HIT, r"line"),
            ),
        )

        assert patterns.translate("line") == {
            _KEY.EVENT_TYPE: _Event.HIT,
            _KEY.RAW: "line",
        }

    def test_unknown_keeps_raw(self) -> None:
        """No match yields an UNKNOWN event that keeps the raw content."""

        patterns = ARLogPatternSet(
            _Event.UNKNOWN, (ARLogPattern(_Event.HIT, r"never"),)
        )

        assert patterns.translate("line") == {
            _KEY.EVENT_TYPE: _Event.UNKNOWN,
            _KEY.RAW: unread("line"),
        }

    def test_no_patterns_is_the_fallback(self) -> None:
        """A set with no patterns leaves every message unknown."""

        assert ARLogPatternSet(_Event.UNKNOWN).translate("line") == {
            _KEY.EVENT_TYPE: _Event.UNKNOWN,
            _KEY.RAW: unread("line"),
        }
