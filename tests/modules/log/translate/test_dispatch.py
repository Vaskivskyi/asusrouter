"""Tests for the program-based log entry dispatch."""

from __future__ import annotations

from asusrouter.modules.common.command import ARService
from asusrouter.modules.log.entry import ARLogEntry, ARLogProgram
from asusrouter.modules.log.enums import AREventKey, ARProgram
from asusrouter.modules.log.translate.dispatch import (
    _translate_content,
    resolve_program,
    translate_entries,
    translate_entry,
)
from asusrouter.modules.log.translate.kernel import AREventKernel
from asusrouter.modules.log.translate.rc_service import AREventRcService
from asusrouter.modules.log.translate.unknown import AREventUnknown
from asusrouter.tools.security.text import SensitiveText
from tests.modules.log.translate import unread


def _entry(name: str | None, content: str) -> ARLogEntry:
    """Build an entry with the given program token and content."""

    program = ARLogProgram(name) if name is not None else None

    return ARLogEntry(
        "Jul 22 08:43:21",
        program=program,
        content=SensitiveText(content),
    )


class TestResolveProgram:
    """Resolving an entry's typed program."""

    def test_known_program(self) -> None:
        """A mapped token resolves to its typed program."""

        assert resolve_program(_entry("kernel", "")) is ARProgram.KERNEL

    def test_aliased_program(self) -> None:
        """An aliased token resolves to the program it stands for."""

        assert resolve_program(_entry("amas_lib", "")) is ARProgram.RC_SERVICE

    def test_indexed_program(self) -> None:
        """An indexed token resolves to its base program."""

        assert resolve_program(_entry("vpnclient5", "")) is (
            ARProgram.VPN_CLIENT
        )

    def test_unmapped_program(self) -> None:
        """A token with no enum member resolves to UNKNOWN."""

        assert resolve_program(_entry("nobody", "")) is ARProgram.UNKNOWN

    def test_no_program(self) -> None:
        """A tag-less entry resolves to UNKNOWN."""

        assert resolve_program(_entry(None, "")) is ARProgram.UNKNOWN


class TestTranslateEntry:
    """Single-entry dispatch."""

    def test_rc_service(self) -> None:
        """An rc_service entry routes to the rc_service translator."""

        entry = _entry("rc_service", "service 2011:notify_rc restart_firewall")

        assert translate_entry(entry) == {
            AREventKey.EVENT_TYPE: AREventRcService.NOTIFY,
            AREventKey.RAW: entry.content.value,
            AREventKey.CALLER: "service",
            AREventKey.PID: 2011,
            AREventKey.SERVICES: (ARService.FIREWALL_RESTART,),
            AREventKey.ACTIONS: ("restart_firewall",),
        }

    def test_kernel(self) -> None:
        """A kernel entry routes to the kernel translator."""

        content = "br0: topology change detected, propagating"
        entry = _entry("kernel", content)

        assert translate_entry(entry)[AREventKey.EVENT_TYPE] is (
            AREventKernel.BRIDGE_TOPOLOGY_CHANGE
        )

    def test_alias(self) -> None:
        """An uppercase `HTTPD` tag aliases to the httpd translator."""

        entry = _entry("HTTPD", "HTTPD: some future httpd message")

        # The httpd dispatcher always returns a dict (UNKNOWN if unmatched)
        assert translate_entry(entry) is not None

    def test_unmapped_program(self) -> None:
        """A program with no translator falls back to unknown."""

        entry = _entry("dnsmasq", "reading /etc/hosts")

        assert translate_entry(entry) == {
            AREventKey.EVENT_TYPE: AREventUnknown.UNKNOWN,
            AREventKey.RAW: unread("reading /etc/hosts"),
        }

    def test_indexed_unmapped(self) -> None:
        """An indexed unmapped program still falls back to unknown."""

        event = translate_entry(_entry("vpnclient5", "Initialization"))

        assert event[AREventKey.EVENT_TYPE] is AREventUnknown.UNKNOWN

    def test_no_program(self) -> None:
        """A tag-less entry falls back to unknown, keeping the raw."""

        assert translate_entry(_entry(None, "syslogd exiting")) == {
            AREventKey.EVENT_TYPE: AREventUnknown.UNKNOWN,
            AREventKey.RAW: unread("syslogd exiting"),
        }

    def test_program_provided(self) -> None:
        """An already-resolved program skips re-resolving the token."""

        content = "br0: topology change detected"
        entry = _entry("kernel", content)

        assert translate_entry(entry, ARProgram.KERNEL) == translate_entry(
            entry
        )

    def test_program_provided_overrides_token(self) -> None:
        """The given program picks the translator, not the entry's token."""

        entry = _entry("kernel", "reading /etc/hosts")

        assert translate_entry(entry, ARProgram.DNSMASQ) == {
            AREventKey.EVENT_TYPE: AREventUnknown.UNKNOWN,
            AREventKey.RAW: unread("reading /etc/hosts"),
        }


class TestTranslateEntries:
    """Batch dispatch."""

    def test_maps_all(self) -> None:
        """Every entry yields an event, 1:1; unmapped marked unknown."""

        entries = [
            _entry("rc_service", "service 2011:notify_rc restart_firewall"),
            _entry("dnsmasq", "reading /etc/hosts"),
            _entry(None, "syslogd exiting"),
            _entry("kernel", "br0: topology change detected"),
        ]

        events = translate_entries(entries)

        assert len(events) == 4
        assert events[0][AREventKey.EVENT_TYPE] is (AREventRcService.NOTIFY)
        assert events[1][AREventKey.EVENT_TYPE] is AREventUnknown.UNKNOWN
        assert events[2][AREventKey.EVENT_TYPE] is AREventUnknown.UNKNOWN
        assert events[3][AREventKey.EVENT_TYPE] is (
            AREventKernel.BRIDGE_TOPOLOGY_CHANGE
        )

    def test_empty(self) -> None:
        """No entries yields no events."""

        assert translate_entries([]) == []


class TestTranslationCache:
    """Reusing the translation of a repeated message."""

    def test_repeat_is_cached(self) -> None:
        """The same message is translated once, however often it repeats."""

        content = "br0: port 7(eth9) entering forwarding state"
        _translate_content.cache_clear()

        translate_entry(_entry("kernel", content))
        translate_entry(_entry("kernel", content))

        info = _translate_content.cache_info()
        assert info.misses == 1
        assert info.hits == 1

    def test_caller_owns_the_result(self) -> None:
        """Each caller gets its own dict, so mutating it is safe."""

        content = "br0: topology change detected"
        first = translate_entry(_entry("kernel", content))
        first.clear()

        assert translate_entry(_entry("kernel", content)) == {
            AREventKey.EVENT_TYPE: AREventKernel.BRIDGE_TOPOLOGY_CHANGE,
            AREventKey.RAW: content,
            AREventKey.BRIDGE: "br0",
        }

    def test_program_is_part_of_the_key(self) -> None:
        """The same text under another program translates on its own."""

        content = "br0: topology change detected"
        assert translate_entry(_entry("kernel", content)) != translate_entry(
            _entry("dnsmasq", content)
        )
