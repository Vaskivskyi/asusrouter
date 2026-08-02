"""Tests for asusrouter.modules.log.probe."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.const import AR_CALL_PROBE_STATE
from asusrouter.modules.log.probe import (
    _POLL_DELAY,
    _SAMPLE_LENGTH,
    async_probe_state,
)
from asusrouter.modules.log.source import ARLogSource, translate_state
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.probe import ARProbeSection
from asusrouter.tools.probe.redact import REDACTED_MAC
from asusrouter.tools.security import ARSecurityLevel

_SOURCE = ARLogSource()

# Two known programs, one of them without a typed member
_LOG = (
    "Jan  1 10:00:00 ntp: start NTP update\n"
    "Jan  1 10:00:01 wlceventd: wlceventd_proc_event(722): "
    "wl0.1: Auth AA:BB:CC:DD:EE:FF, status: Successful (0), rssi:0\n"
    "Jan  1 10:00:02 nosuchd: something nobody translates yet "
    "from AA:BB:CC:DD:EE:FF\n"
)
_TAIL = "Jan  1 10:00:03 ntp: start NTP update\n"


def _sections(result: list[ARProbeSection]) -> dict[str, dict[str, str]]:
    """Index a probe result by section title and row label."""

    return {
        section.title: dict(section.rows)
        for section in result  # noqa: PLR1702 - flat comprehension
    }


class _Device:
    """A fake device answering both reads the probe makes."""

    def __init__(self, *replies: str) -> None:
        """Store the replies to hand out, newest read last."""

        self.replies = list(replies)
        self.reads = 0

    async def async_fetch_raw(self, **kwargs: Any) -> str:
        """Answer one raw read."""

        reply = self.replies[min(self.reads, len(self.replies) - 1)]
        self.reads += 1
        return reply

    async def async_fetch_data(self, source: Any, **kwargs: Any) -> Any:
        """Answer one pipeline read with the first reply."""

        return {source: translate_state(self.replies[0])}


async def _probe(
    device: _Device, level: ARSecurityLevel = ARSecurityLevel.SANITIZED
) -> dict[str, dict[str, str]]:
    """Run the probe against a fake device."""

    return _sections(
        await async_probe_state(
            None,
            _SOURCE,
            fetch_data_callback=device.async_fetch_data,
            fetch_raw_callback=device.async_fetch_raw,
            level=level,
            probe_delay=0.0,
        )
    )


class TestRegistration:
    """Tests for the probe registration."""

    def test_registered(self) -> None:
        """The log source resolves its probe."""

        assert (
            ARCallReg.get_callable(_SOURCE, AR_CALL_PROBE_STATE)
            is async_probe_state
        )

    def test_poll_delay_leaves_the_device_time(self) -> None:
        """The default delay is long enough for the device to write."""

        assert _POLL_DELAY > 0


class TestSections:
    """Tests for the sections the probe builds."""

    async def test_every_section_is_present(self) -> None:
        """A complete probe reports each of its sections once."""

        sections = await _probe(_Device(_LOG))

        assert list(sections) == [
            "buffer",
            "programs",
            "event types",
            "untranslated",
            "incremental read",
            "timing",
        ]

    async def test_buffer(self) -> None:
        """The buffer section counts the entries and holds the anchor."""

        buffer = (await _probe(_Device(_LOG)))["buffer"]

        assert buffer["entries"] == "3"
        assert buffer["total before filtering"] == "3"
        assert buffer["anchor stored"].endswith("chars")

    async def test_buffer_without_entries(self) -> None:
        """An empty log still reports, with no timestamps."""

        buffer = (await _probe(_Device("")))["buffer"]

        assert buffer["entries"] == "0"
        assert buffer["oldest"] == "None"

    async def test_programs(self) -> None:
        """Every program is counted, typed or not."""

        programs = (await _probe(_Device(_LOG)))["programs"]

        assert programs["ntp"] == "1 -> ntp"
        assert programs["nosuchd"] == "1 -> no typed program"

    async def test_event_types(self) -> None:
        """Translated events are counted per program and type."""

        events = (await _probe(_Device(_LOG)))["event types"]

        assert events["ntp start_update"] == "1"
        assert events["wlceventd auth"] == "1"

    async def test_untranslated(self) -> None:
        """An unrecognized message names its program and shows itself."""

        untranslated = (await _probe(_Device(_LOG)))["untranslated"]

        assert untranslated["translated"] == "2/3 (66.7%)"
        assert untranslated["nosuchd"].startswith("1 e.g. ")

    async def test_untranslated_without_events(self) -> None:
        """Nothing to translate counts as fully translated."""

        untranslated = (await _probe(_Device("")))["untranslated"]

        assert untranslated["translated"] == "0/0 (100.0%)"

    async def test_timing(self) -> None:
        """Every measured call reports a duration."""

        timing = (await _probe(_Device(_LOG)))["timing"]

        assert len(timing) == 4
        assert all(value.endswith("ms") for value in timing.values())


class TestRedaction:
    """Tests for what a shared report exposes."""

    async def test_sample_is_scrubbed(self) -> None:
        """The example of an untranslated message hides its addresses."""

        untranslated = (await _probe(_Device(_LOG)))["untranslated"]

        assert REDACTED_MAC in untranslated["nosuchd"]
        assert "AA:BB:CC:DD:EE:FF" not in untranslated["nosuchd"]

    async def test_sample_is_kept_when_allowed(self) -> None:
        """A report asked for raw values keeps the message as written."""

        untranslated = (await _probe(_Device(_LOG), ARSecurityLevel.UNSAFE))[
            "untranslated"
        ]

        assert "AA:BB:CC:DD:EE:FF" in untranslated["nosuchd"]

    async def test_sample_is_cut_after_rendering(self) -> None:
        """An address straddling the cut cannot leave half of itself."""

        long_tag = "nosuchd: " + "x" * _SAMPLE_LENGTH + " AA:BB:CC:DD:EE:FF"
        untranslated = (
            await _probe(_Device(f"Jan  1 10:00:00 {long_tag}\n"))
        )["untranslated"]

        assert "AA:BB" not in untranslated["nosuchd"]


class TestIncremental:
    """Tests for the incremental read section."""

    async def test_continues_from_the_anchor(self) -> None:
        """A grown buffer is parsed from where the first read ended."""

        incremental = (await _probe(_Device(_LOG, _LOG + _TAIL)))[
            "incremental read"
        ]

        assert incremental["first read"] == "3"
        assert incremental["second read, on device"] == "4"
        assert incremental["second read, parsed"] == "1"
        assert incremental["kept across the reads"] == "4"
        assert incremental["anchor"] == "matched, continued"

    async def test_keeps_what_the_device_dropped(self) -> None:
        """Entries trimmed by the device survive in the kept history."""

        incremental = (await _probe(_Device(_LOG, _TAIL)))["incremental read"]

        assert incremental["second read, on device"] == "1"
        assert incremental["kept across the reads"] == "4"

    async def test_unchanged_buffer_is_not_reported_as_proof(self) -> None:
        """A buffer nothing was written to says so, not just "matched"."""

        incremental = (await _probe(_Device(_LOG)))["incremental read"]

        assert incremental["second read, parsed"] == "0"
        assert incremental["anchor"] == (
            "matched, but nothing new was written"
        )

    async def test_reports_a_lost_anchor(self) -> None:
        """A buffer sharing nothing with the last read is read in full."""

        replaced = "Jan  2 11:00:00 crond: time disparity of 5 minutes\n"
        incremental = (await _probe(_Device(_LOG, replaced)))[
            "incremental read"
        ]

        assert incremental["anchor"] == "not found, read in full"

    @pytest.mark.parametrize(
        ("replies", "expected"),
        [
            (("", ""), "the device returned an empty log"),
            ((_LOG, ""), "the second read returned an empty log"),
        ],
    )
    async def test_empty_reads(
        self, replies: tuple[str, str], expected: str
    ) -> None:
        """An empty reply is reported instead of measured."""

        incremental = (await _probe(_Device(*replies)))["incremental read"]

        assert incremental["skipped"] == expected

    async def test_without_a_raw_fetch(self) -> None:
        """Without raw access the section says so rather than failing."""

        device = _Device(_LOG)
        sections = _sections(
            await async_probe_state(
                None,
                _SOURCE,
                fetch_data_callback=device.async_fetch_data,
                probe_delay=0.0,
            )
        )

        assert sections["incremental read"]["skipped"] == (
            "no raw fetch available"
        )


class TestWithoutADevice:
    """Tests for a probe that cannot reach the device."""

    async def test_no_fetch_callback(self) -> None:
        """Nothing is reported when there is no way to fetch."""

        assert await async_probe_state(None, _SOURCE) == []

    async def test_no_data(self) -> None:
        """A source that returned nothing still reports its sections."""

        async def empty(source: Any, **kwargs: Any) -> None:
            return None

        sections = _sections(
            await async_probe_state(
                None,
                _SOURCE,
                fetch_data_callback=empty,
                probe_delay=0.0,
            )
        )

        assert sections["buffer"]["entries"] == "0"
