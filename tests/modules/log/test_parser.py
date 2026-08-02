"""Tests for the log parser."""

from __future__ import annotations

import pytest

from asusrouter.modules.log.entry import ARLogEntry, ARLogProgram
from asusrouter.modules.log.enums import ARProgram
from asusrouter.modules.log.parser import (
    ANCHOR_LENGTH,
    anchor_of,
    find_continuation,
    parse_log,
    parse_program,
    parse_text,
    strip_envelope,
)
from asusrouter.tools.security.text import SensitiveText

_RAW = (
    '{\n"nvram_dump-syslog.log":Jul 21 15:08:01 kernel: first\n'
    "Jul 21 15:08:02 wlceventd: second\n}"
)


class TestStripEnvelope:
    """Envelope stripping."""

    def test_wrapper_removed(self) -> None:
        """The broken-JSON wrapper is removed."""

        text = strip_envelope(_RAW)

        assert text.startswith("Jul 21 15:08:01 kernel: first")
        assert "nvram_dump" not in text
        assert not text.endswith("}")

    def test_raw_passthrough(self) -> None:
        """Already-raw content is returned unchanged."""

        raw = "Jul 21 15:08:01 kernel: first"

        assert strip_envelope(raw) == raw

    @pytest.mark.parametrize("content", [None, "", "   "])
    def test_empty(self, content: str | None) -> None:
        """None or blank content yields an empty string."""

        assert strip_envelope(content) == ""

    def test_colour_escapes_removed(self) -> None:
        """The colour escapes firmware writes are cut out of the text."""

        raw = "Jul 21 15:08:01 kernel: \x1b[0;30;103mWarning: Serdes\x1b[0m"

        assert strip_envelope(raw) == (
            "Jul 21 15:08:01 kernel: Warning: Serdes"
        )

    def test_colour_escapes_reach_the_entry(self) -> None:
        """A coloured message is matchable once it is parsed."""

        raw = "Jul 21 15:08:01 kernel: \x1b[0;30;103mWarning: Serdes"

        assert parse_log(raw)[0].content.value == "Warning: Serdes"

    def test_end_of_buffer_padding_removed(self) -> None:
        """The blank line closing a reply is not kept as log text."""

        raw = '{\n"nvram_dump-syslog.log":Jul 21 15:08:01 ntp: a\n\n}'

        assert strip_envelope(raw) == "Jul 21 15:08:01 ntp: a"


class TestParseLog:
    """Splitting raw replies into entries."""

    def test_wrapped_reply(self) -> None:
        """A wrapped reply parses into ordered entries with timestamp cut."""

        entries = parse_log(_RAW)

        assert entries == [
            ARLogEntry(
                timestamp_str="Jul 21 15:08:01",
                program=ARLogProgram("kernel"),
                content=SensitiveText("first"),
            ),
            ARLogEntry(
                timestamp_str="Jul 21 15:08:02",
                program=ARLogProgram("wlceventd"),
                content=SensitiveText("second"),
            ),
        ]

    def test_space_padded_day(self) -> None:
        """A single-digit day padded with a space is split correctly."""

        raw = (
            "Aug  1 02:35:45 ntp: start NTP update\n"
            "Aug  1 02:36:15 ntp: start NTP update"
        )

        entries = parse_log(raw)

        assert len(entries) == 2
        assert entries[0].timestamp_str == "Aug  1 02:35:45"
        assert entries[0].content.value == "start NTP update"

    def test_timestamp_cut_from_message(self) -> None:
        """The timestamp is not duplicated inside the message."""

        entry = parse_log("Jul 21 15:08:01 kernel: boot")[0]

        assert entry.timestamp_str == "Jul 21 15:08:01"
        assert entry.content.value == "boot"

    def test_pid_kept_in_message(self) -> None:
        """A service `[pid]` token stays in message but splits into fields."""

        entry = parse_log("Aug  1 02:43:59 miniupnpd[1337]: chain gone")[0]

        assert entry.content.value == "chain gone"
        assert entry.program == ARLogProgram("miniupnpd", 1337)
        assert entry.content.value == "chain gone"

    def test_service_and_content_split(self) -> None:
        """A plain service is split from its content on the first colon."""

        entry = parse_log("Aug  1 02:35:45 ntp: start NTP update")[0]

        assert entry.program == ARLogProgram("ntp", None)
        assert entry.content.value == "start NTP update"

    def test_multi_word_service_split(self) -> None:
        """A multi-word service is captured whole, not cut at a space."""

        entry = parse_log("Jul 22 03:29:38 dhcp client: deconfig")[0]

        assert entry.program == ARLogProgram("dhcp client")
        assert entry.content.value == "deconfig"

    def test_content_with_colons(self) -> None:
        """Only the first colon splits service; content keeps its colons."""

        entry = parse_log("Jul 21 15:08:02 wlceventd: proc(6): wl0: up")[0]

        assert entry.program == ARLogProgram("wlceventd")
        assert entry.content.value == "proc(6): wl0: up"

    def test_message_without_colon(self) -> None:
        """A message with no colon has no service, content is the message."""

        entry = parse_log("Jul 21 15:08:02 just a bare line")[0]

        assert entry.program is None
        assert entry.content.value == "just a bare line"

    def test_freeform_syslogd_started(self) -> None:
        """A freeform `syslogd started` line maps to syslogd, keeps message."""

        raw = "Aug  3 18:19:46 syslogd started: BusyBox v1.25.1"

        entry = parse_log(raw)[0]

        assert entry.program == ARLogProgram("syslogd")
        assert entry.content.value == "syslogd started: BusyBox v1.25.1"

    def test_freeform_syslogd_exiting(self) -> None:
        """A freeform `syslogd exiting` line maps to syslogd, keeps message."""

        entry = parse_log("Aug  1 03:41:52 syslogd exiting")[0]

        assert entry.program == ARLogProgram("syslogd")
        assert entry.content.value == "syslogd exiting"

    def test_real_syslogd_tag_still_splits(self) -> None:
        """A real `syslogd:` tag is not treated as freeform."""

        entry = parse_log("Aug  1 03:41:52 syslogd: normal message")[0]

        assert entry.program == ARLogProgram("syslogd")
        assert entry.content.value == "normal message"

    def test_empty_service_name(self) -> None:
        """A message starting with a colon has no service."""

        entry = parse_log("Jul 21 15:08:02 : orphan content")[0]

        assert entry.program is None
        assert entry.content.value == "orphan content"

    def test_multi_word_service_kept(self) -> None:
        """A service name containing a space is not a false boundary."""

        raw = (
            "Jul 22 03:29:25 WAN(0) Connection: link up "
            "Jul 22 03:29:38 dhcp client: deconfig"
        )

        entries = parse_log(raw)

        assert len(entries) == 2
        assert entries[0].program == ARLogProgram("WAN(0) Connection")
        assert entries[1].program == ARLogProgram("dhcp client")

    def test_space_joined_records_split(self) -> None:
        """Records jammed onto one line (no newline) still split."""

        raw = (
            "Jul 22 08:53:29 vpnserver1[20330]: reset "
            "Jul 22 08:53:31 ARK: ARK is blocked"
        )

        entries = parse_log(raw)

        assert len(entries) == 2
        assert entries[0].program == ARLogProgram("vpnserver1", 20330)
        assert entries[1].content.value == "ARK is blocked"

    def test_embedded_newline_absorbed(self) -> None:
        """A message with an embedded newline stays one entry."""

        raw = (
            "Jul 22 08:53:29 vpnserver1[20330]: WARNING bad packet\n"
            "            <=1768 please ensure\n"
            "Jul 22 08:53:31 ARK: blocked"
        )

        entries = parse_log(raw)

        assert len(entries) == 2
        assert "please ensure" in entries[0].content.value
        assert entries[1].content.value == "blocked"

    def test_order_preserved(self) -> None:
        """Entries keep buffer order, never sorted by timestamp."""

        raw = "Aug  1 02:00:00 ntp: later Jul 31 23:59:59 ntp: earlier"

        entries = parse_log(raw)

        assert [entry.timestamp_str for entry in entries] == [
            "Aug  1 02:00:00",
            "Jul 31 23:59:59",
        ]

    @pytest.mark.parametrize("content", [None, "", "no timestamp here"])
    def test_no_records(self, content: str | None) -> None:
        """Empty or headless content yields no entries."""

        assert parse_log(content) == []

    def test_program_shared_between_entries(self) -> None:
        """Entries of one emitter share a single program object."""

        raw = (
            "Jul 22 08:43:21 ntp: start NTP update\n"
            "Jul 22 08:43:22 ntp: start NTP update\n"
            "Jul 22 08:43:23 httpd[123]: other\n"
        )

        first, second, third = parse_log(raw)

        assert first.program is second.program
        assert first.program is not third.program

    def test_pid_keeps_emitters_apart(self) -> None:
        """The same name under another pid is a different emitter."""

        raw = "Jul 22 08:43:21 httpd[1]: a\nJul 22 08:43:22 httpd[2]: b\n"

        first, second = parse_log(raw)

        assert first.program is not second.program
        assert first.program != second.program


class TestParseProgram:
    """Splitting a raw token into a kind and index."""

    def test_plain_program(self) -> None:
        """A non-indexed known program has no index."""

        assert parse_program("miniupnpd") == (ARProgram.MINIUPNP, None)

    def test_indexed_program(self) -> None:
        """An indexed known program yields its base kind and index."""

        assert parse_program("vpnclient5") == (ARProgram.VPN_CLIENT, 5)

    def test_indexed_server(self) -> None:
        """The index is parsed as an int."""

        assert parse_program("vpnserver2") == (ARProgram.VPN_SERVER, 2)

    def test_unknown_indexed_keeps_no_index(self) -> None:
        """Digits on an unknown base do not produce a spurious index."""

        assert parse_program("foo3") == (ARProgram.UNKNOWN, None)

    def test_hyphenated_not_indexed(self) -> None:
        """A hyphenated program without trailing digits keeps no index."""

        assert parse_program("dnsmasq-dhcp") == (ARProgram.DNSMASQ_DHCP, None)

    def test_unknown_plain(self) -> None:
        """An unknown non-indexed token resolves to UNKNOWN, no index."""

        assert parse_program("nosuchd") == (ARProgram.UNKNOWN, None)

    def test_alias_semantic(self) -> None:
        """An aliased token resolves to its mapped program (amas_lib)."""

        assert parse_program("amas_lib") == (ARProgram.RC_SERVICE, None)

    def test_alias_case(self) -> None:
        """The uppercase HTTPD tag resolves to the web daemon."""

        assert parse_program("HTTPD") == (ARProgram.HTTP_DAEMON, None)


def _text(first: int, last: int) -> str:
    """Build a run of distinct records as raw log text."""

    return "\n".join(
        f"Jul 21 {index // 3600:02d}:{index // 60 % 60:02d}:{index % 60:02d} "
        f"kernel: line {index}"
        for index in range(first, last)
    )


class TestAnchorOf:
    """The tail kept to continue the next read from."""

    def test_short_text_kept_whole(self) -> None:
        """A text shorter than the window is its own anchor."""

        text = _text(0, 5)

        assert anchor_of(text) == text

    def test_long_text_trimmed(self) -> None:
        """A long text yields only its tail."""

        text = _text(0, 2000)
        anchor = anchor_of(text)

        assert len(anchor) == ANCHOR_LENGTH
        assert text.endswith(anchor)


class TestFindContinuation:
    """Locating the records new since an earlier read."""

    def test_whole_anchor_present(self) -> None:
        """An untrimmed log continues right after the anchor."""

        previous = _text(0, 40)
        text = previous + "\n" + _text(40, 45)

        offset = find_continuation(text, previous)

        assert text[offset:].strip().startswith("Jul 21 00:00:40")

    def test_anchor_partly_trimmed(self) -> None:
        """A log that dropped into the anchor continues after what is left."""

        previous = _text(0, 40)
        text = _text(20, 60)

        offset = find_continuation(text, previous)

        assert offset is not None
        assert text[offset:].strip().startswith("Jul 21 00:00:40")

    def test_nothing_in_common(self) -> None:
        """A text sharing not one character with the anchor cannot continue."""

        assert find_continuation("aaa", "zzz") is None

    def test_chance_overlap_rejected(self) -> None:
        """An overlap too short to span whole records is not believed."""

        # both end on the same few characters, sharing no whole record
        assert find_continuation("Jul 21 00:00:09 ntp: x", "zzz x") is None

    def test_no_overlap(self) -> None:
        """A log sharing nothing with the anchor cannot be continued."""

        assert find_continuation(_text(500, 540), _text(0, 40)) is None

    def test_empty_anchor(self) -> None:
        """Without an anchor there is nothing to continue from."""

        assert find_continuation(_text(0, 5), "") is None

    def test_unchanged_log(self) -> None:
        """A log that gained nothing continues at its very end."""

        text = _text(0, 40)

        assert find_continuation(text, text) == len(text)

    def test_repeated_message_does_not_mislead(self) -> None:
        """One message repeated under its own stamp still continues right."""

        def spam(first: int, last: int) -> str:
            return "\n".join(
                f"Jul 21 00:{index // 60:02d}:{index % 60:02d} "
                "ntp: start NTP update"
                for index in range(first, last)
            )

        previous = spam(0, 400)
        text = previous + "\n" + spam(400, 405)

        offset = find_continuation(text, previous)

        assert offset is not None
        assert len(parse_text(text[offset:])) == 5

    def test_identical_records_are_treated_as_seen(self) -> None:
        """Records identical down to the stamp cannot be told apart.

        Nothing distinguishes the newest from the ones already read, so
        they count as already seen rather than being read twice.
        """

        line = "Jul 21 00:00:01 ntp: start NTP update"
        previous = "\n".join([line] * 400)
        text = previous + "\n" + "\n".join([line] * 5)

        assert find_continuation(text, previous) == len(text)


class TestParseContinued:
    """Parsing only what is new."""

    def test_after_reads_the_tail_only(self) -> None:
        """`after` limits the parse to the records that followed it."""

        previous = _text(0, 40)
        raw = (
            '{"nvram_dump-syslog.log":' + previous + "\n" + _text(40, 45) + "}"
        )

        entries = parse_log(raw, after=previous)

        assert [entry.content.value for entry in entries] == [
            f"line {index}" for index in range(40, 45)
        ]

    def test_unusable_anchor_reads_everything(self) -> None:
        """An anchor from another log falls back to reading it all."""

        raw = '{"nvram_dump-syslog.log":' + _text(0, 10) + "}"

        assert len(parse_log(raw, after=_text(900, 940))) == 10


class TestUntaggedProgram:
    """Recovering the writer of a message the device left untagged."""

    def test_empty_tag_recovered(self) -> None:
        """`: fwver: ...` names init the way `init: fwver: ...` does."""

        entry = parse_log("Jul 21 15:08:01 : fwver: 3.0.0.4 (sn:X /ha:Y )")[0]

        assert entry.program == ARLogProgram("init")
        assert entry.content.value.startswith("fwver: 3.0.0.4")

    def test_both_spellings_agree(self) -> None:
        """Tagged and untagged forms leave exactly the same entry behind."""

        untagged = parse_log("Jul 21 15:08:01 : fwver: 3.0.0.4")[0]
        tagged = parse_log("Jul 21 15:08:01 init: fwver: 3.0.0.4")[0]

        assert untagged.program == tagged.program
        assert untagged.content.value == tagged.content.value

    def test_other_empty_tags_stay_untagged(self) -> None:
        """A tag-less line nobody claims keeps having no program."""

        entry = parse_log("Jul 21 15:08:01 : something else entirely")[0]

        assert entry.program is None
        assert entry.content.value == "something else entirely"
