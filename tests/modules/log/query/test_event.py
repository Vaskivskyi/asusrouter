"""Tests for the processed log event envelope."""

from __future__ import annotations

from datetime import UTC, datetime

from asusrouter.modules.common.command import ARService
from asusrouter.modules.log.entry import ARLogEntry, ARLogProgram
from asusrouter.modules.log.enums import AREventKey, ARProgram
from asusrouter.modules.log.query.event import build_event, build_events
from asusrouter.modules.log.translate.ntp import AREventNtp
from asusrouter.modules.log.translate.rc_service import AREventRcService
from asusrouter.modules.log.translate.unknown import AREventUnknown
from asusrouter.tools.security.text import SensitiveText


def _entry(name: str | None, content: str) -> ARLogEntry:
    """Build an entry with a resolved program tag."""

    program = ARLogProgram(name) if name is not None else None

    return ARLogEntry(
        "Jul 22 08:43:21",
        program=program,
        content=SensitiveText(content),
    )


class TestBuildEvent:
    """Translating a single entry into an envelope."""

    def test_metadata_lifted(self) -> None:
        """Program, event type and raw move onto the envelope."""

        event = build_event(_entry("ntp", "start NTP update"))

        assert event.program is ARProgram.NTP
        assert event.program_name == "ntp"
        assert event.event_type is AREventNtp.START_UPDATE
        assert event.raw == "start NTP update"
        assert event.data == {}
        assert event.facets == frozenset()

    def test_hashable(self) -> None:
        """The envelope hashes despite carrying a mutable data payload."""

        content = "udhcpc_wan 1657:notify_rc restart_wan"
        entry = _entry("rc_service", content)

        assert build_event(entry).data
        assert hash(build_event(entry)) == hash(build_event(entry))
        assert len({build_event(entry), build_event(entry)}) == 1

    def test_data_excludes_metadata(self) -> None:
        """The data payload drops EVENT_TYPE/RAW, keeping only fields."""

        content = "udhcpc_wan 1657:notify_rc restart_wan;restart_firewall"
        event = build_event(_entry("rc_service", content))

        assert event.event_type is AREventRcService.NOTIFY
        assert AREventKey.EVENT_TYPE not in event.data
        assert AREventKey.RAW not in event.data
        assert event.data[AREventKey.CALLER] == "udhcpc_wan"

    def test_facets_derived(self) -> None:
        """Facets are derived from the payload (SERVICES -> SERVICE axis)."""

        content = "udhcpc_wan 1657:notify_rc restart_wan;restart_firewall"
        event = build_event(_entry("rc_service", content))

        assert event.facets == frozenset(
            {
                (AREventKey.CALLER, "udhcpc_wan"),
                (AREventKey.SERVICE, ARService.WAN_RESTART),
                (AREventKey.SERVICE, ARService.FIREWALL_RESTART),
            }
        )

    def test_tagless_is_unknown(self) -> None:
        """A tag-less entry resolves to UNKNOWN program, empty data."""

        event = build_event(_entry(None, "bare line"))

        assert event.program is ARProgram.UNKNOWN
        assert event.program_name is None
        assert event.event_type is AREventUnknown.UNKNOWN
        assert event.data == {}

    def test_untyped_program_keeps_its_tag(self) -> None:
        """A program with no typed member is still named on the envelope."""

        event = build_event(_entry("ARK", "ARK is blocked, reason=3!!"))

        assert event.program is ARProgram.UNKNOWN
        assert event.program_name == "ARK"


class TestBuildEvents:
    """Building envelopes from a raw log blob."""

    def test_parses_and_resolves(self) -> None:
        """Each record becomes an envelope with a resolved timestamp."""

        raw = (
            "Jul 22 08:43:21 ntp: start NTP update\n"
            "Jul 22 08:43:22 rc_service: cfg 1:notify_rc restart_wan\n"
        )

        events = build_events(raw, anchor=datetime(2026, 1, 1, tzinfo=UTC))

        assert [event.program for event in events] == [
            ARProgram.NTP,
            ARProgram.RC_SERVICE,
        ]
        assert all(event.timestamp is not None for event in events)

    def test_empty(self) -> None:
        """An empty blob yields no events."""

        assert build_events("") == []


class TestRawText:
    """Reaching the message behind whatever level `raw` carries."""

    def test_classified_raw_reaches_its_value(self) -> None:
        """A classified message hands over its text, not the redaction."""

        event = build_event(_entry("dnsmasq", "reading /etc/hosts"))

        assert isinstance(event.raw, SensitiveText)
        assert str(event.raw) != "reading /etc/hosts"
        assert event.raw_text == "reading /etc/hosts"

    def test_plain_raw_passes_through(self) -> None:
        """A message a translator read in full is already plain text."""

        event = build_event(_entry("ntp", "start NTP update"))

        assert event.raw == "start NTP update"
        assert event.raw_text == "start NTP update"
