"""Tests for free-text scrubbing."""

from __future__ import annotations

import pytest

from asusrouter.tools.probe.redact import REDACTED_IP, REDACTED_MAC, scrub_text


class TestScrubText:
    """Tests for scrub_text."""

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            # Nothing to hide
            ("start NTP update", "start NTP update"),
            ("", ""),
            # MAC, both separators and both cases
            (
                "Assoc AA:BB:CC:DD:EE:FF done",
                f"Assoc {REDACTED_MAC} done",
            ),
            (
                "deauth aa-bb-cc-dd-ee-ff",
                f"deauth {REDACTED_MAC}",
            ),
            # IPv4
            ("bound 192.168.1.15/24", f"bound {REDACTED_IP}/24"),
            (
                "connect(10.0.0.1:2869)",
                f"connect({REDACTED_IP}:2869)",
            ),
            # IPv6
            (
                "peer 2001:0db8:0000:0000:0000:ff00:0042:8329 up",
                f"peer {REDACTED_IP} up",
            ),
            # A time of day is not an address
            (
                "restarted at 12:43:08 today",
                "restarted at 12:43:08 today",
            ),
            # Several identifiers in one message
            (
                "AA:BB:CC:DD:EE:FF asked 192.168.1.1",
                f"{REDACTED_MAC} asked {REDACTED_IP}",
            ),
        ],
    )
    def test_scrubbing(self, text: str, expected: str) -> None:
        """Identifiers are replaced and the rest of the text is kept."""

        assert scrub_text(text) == expected

    def test_is_idempotent(self) -> None:
        """Scrubbing an already scrubbed message changes nothing."""

        once = scrub_text("client AA:BB:CC:DD:EE:FF at 192.168.1.5")

        assert scrub_text(once) == once
