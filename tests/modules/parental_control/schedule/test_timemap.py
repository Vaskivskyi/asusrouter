"""Tests for the timemap model and codec."""

from __future__ import annotations

import pytest

from asusrouter.modules.parental_control.enums import (
    ARParentalControlScheduleMode,
    ARWeekday,
)
from asusrouter.modules.parental_control.schedule.timemap import (
    DAILY,
    WEEKDAYS,
    WEEKEND,
    ARScheduleEntry,
    apply_mode,
    parse_timemap,
    serialize_timemap,
    timemap_mode,
)

_M = ARParentalControlScheduleMode
_D = ARWeekday


class TestDayGroups:
    """The preset day-group constants match the device bitmaps."""

    def test_daily(self) -> None:
        """Daily covers every weekday (bitmap 127)."""

        assert len(DAILY) == 7

    def test_weekdays(self) -> None:
        """Weekdays are Monday through Friday (bitmap 62)."""

        assert {
            _D.MONDAY,
            _D.TUESDAY,
            _D.WEDNESDAY,
            _D.THURSDAY,
            _D.FRIDAY,
        } == WEEKDAYS

    def test_weekend(self) -> None:
        """Weekend is Sunday and Saturday (bitmap 65)."""

        assert {_D.SUNDAY, _D.SATURDAY} == WEEKEND


class TestParse:
    """Tests for parse_timemap."""

    def test_empty(self) -> None:
        """An empty or non-string timemap yields no entries."""

        assert parse_timemap("") == []
        assert parse_timemap(None) == []

    def test_single_entry(self) -> None:
        """A weekday offline entry decodes all of its fields."""

        [entry] = parse_timemap("W03E21000700")
        assert entry.days == WEEKDAYS
        assert (entry.start_hour, entry.start_minute) == (21, 0)
        assert (entry.end_hour, entry.end_minute) == (7, 0)
        assert entry.enable is False

    def test_multiple_entries_decoded(self) -> None:
        """Encoded separators split into aligned entries."""

        entries = parse_timemap("W13E17002100&#60M14116002200")
        assert len(entries) == 2
        assert entries[0].days == WEEKDAYS
        assert entries[0].enable is True
        assert entries[1].days == WEEKEND

    def test_cross_midnight_single_entry(self) -> None:
        """A window past midnight stays one entry with end before start."""

        [entry] = parse_timemap("W04122000600")
        assert entry.days == WEEKEND
        assert (entry.start_hour, entry.end_hour) == (22, 6)

    def test_end_hour_24(self) -> None:
        """An end hour of 24 is preserved."""

        [entry] = parse_timemap("W17F09002400")
        assert entry.days == DAILY
        assert entry.end_hour == 24

    def test_malformed_length_skipped(self) -> None:
        """A token of the wrong length is dropped."""

        assert parse_timemap("W03E210007") == []

    def test_malformed_value_skipped(self) -> None:
        """A token with non-numeric time fields is dropped."""

        assert parse_timemap("W03EXX000700") == []


class TestSerialize:
    """Tests for serialize_timemap."""

    def test_empty(self) -> None:
        """No entries serialize to an empty string."""

        assert serialize_timemap([]) == ""

    def test_offline_prefix(self) -> None:
        """Offline entries carry the W prefix."""

        entry = ARScheduleEntry(
            days=WEEKDAYS, start_hour=21, end_hour=7, enable=False
        )
        assert serialize_timemap([entry], _M.OFFLINE) == "W03E21000700"

    def test_online_prefix(self) -> None:
        """Online entries carry the M prefix."""

        entry = ARScheduleEntry(days=WEEKDAYS, start_hour=17, end_hour=21)
        assert serialize_timemap([entry], _M.ONLINE) == "M13E17002100"

    def test_unknown_mode_defaults_offline(self) -> None:
        """An unknown mode falls back to the offline prefix."""

        entry = ARScheduleEntry(days=DAILY, end_hour=24)
        assert serialize_timemap([entry], _M.UNKNOWN).startswith("W")

    def test_default_mode_offline(self) -> None:
        """The default mode is offline."""

        entry = ARScheduleEntry(days=WEEKEND)
        assert serialize_timemap([entry]).startswith("W")


class TestRoundTrip:
    """Parsing then serializing reproduces the input string."""

    @pytest.mark.parametrize(
        ("raw", "mode"),
        [
            ("W03E21000700<W04122000800", _M.OFFLINE),
            ("M13E17002100<M14116002200", _M.ONLINE),
            ("W17F00002400", _M.OFFLINE),
        ],
    )
    def test_round_trip(self, raw: str, mode: _M) -> None:
        """Every entry survives a decode/encode cycle byte-for-byte."""

        assert serialize_timemap(parse_timemap(raw), mode) == raw


class TestApplyMode:
    """Tests for apply_mode."""

    def test_rewrites_prefixes(self) -> None:
        """Every entry prefix is switched to the given mode."""

        raw = "W03E21000700<W04122000800"
        assert apply_mode(raw, _M.ONLINE) == "M03E21000700<M04122000800"

    def test_unknown_mode_noop(self) -> None:
        """An unknown mode leaves the string untouched."""

        raw = "W03E21000700"
        assert apply_mode(raw, _M.UNKNOWN) == raw

    def test_empty_noop(self) -> None:
        """An empty timemap is returned unchanged."""

        assert apply_mode("", _M.ONLINE) == ""


class TestTimemapMode:
    """Tests for timemap_mode."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("W03E21000700", _M.OFFLINE),
            ("M13E17002100", _M.ONLINE),
            ("", _M.UNKNOWN),
            ("&#60W03E21000700", _M.UNKNOWN),
        ],
    )
    def test_mode(self, raw: str, expected: _M) -> None:
        """The mode comes from the first decoded character."""

        assert timemap_mode(raw) is expected
