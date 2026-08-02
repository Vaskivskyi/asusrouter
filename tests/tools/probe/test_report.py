"""Tests for probe report."""

from __future__ import annotations

from asusrouter.tools.identifiers import MacAddress
from asusrouter.tools.probe.redact import REDACTED_IP, REDACTED_MAC
from asusrouter.tools.probe.report import (
    ARProbeReport,
    ARProbeSection,
    build_section,
    render_value,
)
from asusrouter.tools.security import REDACTED_STR, ARSecurityLevel, Sensitive

_MAC = "AA:BB:CC:DD:EE:FF"


class TestRenderValue:
    """Tests for render_value."""

    def test_plain_value(self) -> None:
        """A value carrying nothing sensitive is only stringified."""

        assert render_value(42, ARSecurityLevel.STRICT) == "42"

    def test_text_is_scrubbed(self) -> None:
        """Free text has its identifiers replaced below the reveal level."""

        rendered = render_value(
            f"client {_MAC} at 192.168.1.5", ARSecurityLevel.SANITIZED
        )

        assert rendered == f"client {REDACTED_MAC} at {REDACTED_IP}"

    def test_text_is_kept_when_allowed(self) -> None:
        """Free text is left alone from the reveal level upwards."""

        text = f"client {_MAC}"

        assert render_value(text, ARSecurityLevel.REASONABLE) == text

    def test_sensitive_value_is_masked(self) -> None:
        """A maskable type is masked, not scrubbed as text."""

        rendered = render_value(MacAddress(_MAC), ARSecurityLevel.SANITIZED)

        # A stable stand-in, so the same client stays recognizable
        assert rendered not in (_MAC, REDACTED_MAC, REDACTED_STR)
        assert rendered == render_value(
            MacAddress(_MAC), ARSecurityLevel.SANITIZED
        )

    def test_sensitive_value_is_revealed(self) -> None:
        """A sensitive value is shown raw at or above its reveal level."""

        rendered = render_value(MacAddress(_MAC), ARSecurityLevel.UNSAFE)

        assert rendered == _MAC.lower()

    def test_sensitive_value_is_redacted(self) -> None:
        """A value that cannot be masked is hidden below its level."""

        value = Sensitive("secret", ARSecurityLevel.UNSAFE)

        assert render_value(value, ARSecurityLevel.STRICT) == REDACTED_STR


class TestBuildSection:
    """Tests for build_section."""

    def test_renders_every_row(self) -> None:
        """Labels are kept as given and values are rendered at the level."""

        section = build_section(
            "buffer",
            [("entries", 12), ("newest", f"from {_MAC}")],
            level=ARSecurityLevel.SANITIZED,
        )

        assert section == ARProbeSection(
            "buffer",
            (("entries", "12"), ("newest", f"from {REDACTED_MAC}")),
        )

    def test_no_rows(self) -> None:
        """A section without rows is still a section."""

        section = build_section("empty", [], level=ARSecurityLevel.STRICT)

        assert section.rows == ()


class TestARProbeReport:
    """Tests for ARProbeReport."""

    def test_defaults(self) -> None:
        """A report holds no sections until they are given."""

        report = ARProbeReport(
            source="ARLogSource", level=ARSecurityLevel.SANITIZED
        )

        assert report.sections == ()
