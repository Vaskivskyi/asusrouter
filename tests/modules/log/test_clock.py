"""Tests for log timestamp resolution."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from asusrouter.modules.log.clock import resolve_datetimes
from asusrouter.modules.log.entry import ARLogEntry
from asusrouter.tools.security.text import SensitiveText

# The device states the offset it wrote the stamps in
_CEST = timezone(timedelta(hours=2))
_ANCHOR = datetime(2026, 1, 1, tzinfo=_CEST)


def _entry(timestamp_str: str) -> ARLogEntry:
    """Build a bare entry with only a timestamp string."""

    return ARLogEntry(timestamp_str=timestamp_str, content=SensitiveText("x"))


class TestResolveDatetimes:
    """Assigning a best-effort datetime to each entry."""

    def test_empty(self) -> None:
        """No entries resolve to nothing."""

        assert resolve_datetimes([]) == []

    def test_mutates_in_place(self) -> None:
        """Resolution sets the timestamp on the same entry objects."""

        entries = [_entry("Jul 21 15:08:01")]

        result = resolve_datetimes(entries, anchor=_ANCHOR)

        assert result is entries
        assert entries[0].timestamp == datetime(
            2026, 7, 21, 15, 8, 1, tzinfo=_CEST
        )

    def test_anchor_year_applied(self) -> None:
        """The given anchor year is used for the newest entry."""

        result = resolve_datetimes([_entry("Jul 21 15:08:01")], anchor=_ANCHOR)

        assert result[0].timestamp == datetime(
            2026, 7, 21, 15, 8, 1, tzinfo=_CEST
        )

    def test_default_anchor_is_current_year(self) -> None:
        """Without an anchor the current year is used."""

        result = resolve_datetimes([_entry("Jul 21 15:08:01")])

        assert result[0].timestamp is not None
        assert result[0].timestamp.year == datetime.now().year

    def test_year_wrap_backwards(self) -> None:
        """Going back across Jan->Dec drops the year for older entries."""

        entries = [_entry("Dec 31 23:59:59"), _entry("Jan 01 00:00:05")]

        result = resolve_datetimes(entries, anchor=_ANCHOR)

        assert result[1].timestamp == datetime(
            2026, 1, 1, 0, 0, 5, tzinfo=_CEST
        )
        assert result[0].timestamp == datetime(
            2025, 12, 31, 23, 59, 59, tzinfo=_CEST
        )

    def test_month_jitter_no_wrap(self) -> None:
        """A one-month backward jitter does not trigger a year change."""

        entries = [_entry("Jul 31 23:59:59"), _entry("Aug 01 00:00:05")]

        result = resolve_datetimes(entries, anchor=_ANCHOR)

        assert result[0].timestamp == datetime(
            2026, 7, 31, 23, 59, 59, tzinfo=_CEST
        )
        assert result[1].timestamp == datetime(
            2026, 8, 1, 0, 0, 5, tzinfo=_CEST
        )

    def test_unparseable_stamp_stays_none(self) -> None:
        """An entry with an unparseable stamp keeps timestamp None."""

        result = resolve_datetimes([_entry("not a stamp")])

        assert result[0].timestamp is None

    def test_invalid_date_stays_none(self) -> None:
        """A calendar-invalid stamp resolves to None, not a crash."""

        result = resolve_datetimes([_entry("Feb 30 00:00:00")], anchor=_ANCHOR)

        assert result[0].timestamp is None

    def test_short_stamp_stays_none(self) -> None:
        """A stamp missing its clock resolves to None."""

        assert resolve_datetimes([_entry("Jul 21")])[0].timestamp is None

    def test_partial_clock_stays_none(self) -> None:
        """A clock without seconds resolves to None."""

        result = resolve_datetimes([_entry("Jul 21 15:08")])

        assert result[0].timestamp is None

    def test_non_numeric_stamp_stays_none(self) -> None:
        """A stamp-shaped token with non-numeric parts resolves to None."""

        result = resolve_datetimes([_entry("Jul xx 15:08:01")])

        assert result[0].timestamp is None

    def test_unknown_month_stays_none(self) -> None:
        """A stamp-shaped token with a non-month word resolves to None."""

        result = resolve_datetimes([_entry("Zzz 01 00:00:00")])

        assert result[0].timestamp is None


class TestHostFallback:
    """Standing in for a device that stated no clock of its own."""

    def test_host_offset_is_used(self) -> None:
        """Every timestamp is placed on a timeline, never left bare."""

        result = resolve_datetimes([_entry("Jul 21 15:08:01")])

        timestamp = result[0].timestamp
        assert timestamp is not None
        assert timestamp.utcoffset() == datetime.now().astimezone().utcoffset()

    def test_future_stamp_takes_the_year_before(self) -> None:
        """A stamp the host's year would date ahead crossed New Year."""

        now = datetime.now().astimezone()
        ahead = now + timedelta(days=60)

        result = resolve_datetimes([_entry(ahead.strftime("%b %d %H:%M:%S"))])

        assert result[0].timestamp is not None
        assert result[0].timestamp <= now + timedelta(days=1)

    def test_unparseable_newest_falls_back_to_host_year(self) -> None:
        """A newest stamp that will not parse leaves the year as it is."""

        result = resolve_datetimes(
            [_entry("Jul 21 15:08:01"), _entry("not a stamp")]
        )

        assert result[0].timestamp is not None
        assert result[0].timestamp.year == datetime.now().year

    def test_invalid_newest_stamp_is_skipped(self) -> None:
        """A calendar-invalid newest stamp does not decide the year."""

        result = resolve_datetimes(
            [_entry("Jul 21 15:08:01"), _entry("Feb 30 00:00:00")]
        )

        assert result[1].timestamp is None
        assert result[0].timestamp is not None
        assert result[0].timestamp.tzinfo is not None

    def test_naive_anchor_falls_back_to_the_host(self) -> None:
        """An anchor with no offset settles nothing; the host stands in."""

        result = resolve_datetimes(
            [_entry("Jul 21 15:08:01")], datetime(2019, 1, 1)
        )

        timestamp = result[0].timestamp
        assert timestamp is not None
        assert timestamp.tzinfo is not None
        assert timestamp.year == datetime.now().year
