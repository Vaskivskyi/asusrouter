"""Tests for probe report writing."""

from __future__ import annotations

from pathlib import Path

import pytest

from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.firmware.version import ARFirmware
from asusrouter.tools.probe.report import ARProbeReport, ARProbeSection
from asusrouter.tools.probe.writer import (
    PROBE_SENSITIVE_WARNING,
    UNKNOWN_IDENTITY,
    _path_token,
    format_report,
    write_probe,
)
from asusrouter.tools.security import ARSecurityLevel

_REPORT = ARProbeReport(
    source="ARLogSource",
    level=ARSecurityLevel.SANITIZED,
    sections=(
        ARProbeSection("buffer", (("entries", "12"),)),
        ARProbeSection("empty", ()),
    ),
)


@pytest.fixture
def identity() -> ARDeviceIdentity:
    """Build a device identity complete enough to name a report."""

    value = ARDeviceIdentity()
    value._model = "RT-AX88U"
    value._firmware = ARFirmware(
        major=(3, 0, 0, 4), minor=388, build=24762, revision=1
    )
    return value


class TestPathToken:
    """Tests for _path_token."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("RT-AX88U", "RT-AX88U"),
            ("3.0.0.4.388_24762", "3.0.0.4.388_24762"),
            ("GT/BE19000 AI", "GT_BE19000_AI"),
            ("", UNKNOWN_IDENTITY),
            (None, UNKNOWN_IDENTITY),
            # Nothing survives the substitution but the separators
            ("///", UNKNOWN_IDENTITY),
        ],
    )
    def test_token(self, value: str | None, expected: str) -> None:
        """A value is reduced to a token usable in a file name."""

        assert _path_token(value) == expected


class TestFormatReport:
    """Tests for format_report."""

    def test_holds_the_context(self, identity: ARDeviceIdentity) -> None:
        """The header names the device, the source and the level."""

        text = format_report(_REPORT, identity)

        assert "RT-AX88U" in text
        assert "ARLogSource" in text
        assert "SANITIZED" in text
        assert PROBE_SENSITIVE_WARNING in text

    def test_holds_the_sections(self, identity: ARDeviceIdentity) -> None:
        """Every section title and row reaches the text."""

        text = format_report(_REPORT, identity)

        assert "--- buffer " in text
        assert "--- empty " in text
        assert "entries" in text
        assert text.endswith("\n")

    def test_long_label_keeps_a_separator(
        self, identity: ARDeviceIdentity
    ) -> None:
        """A label wider than the column does not glue itself to its value."""

        report = ARProbeReport(
            source="ARLogSource",
            level=ARSecurityLevel.SANITIZED,
            sections=(ARProbeSection("wide", (("x" * 40, "29"),)),),
        )

        assert f"{'x' * 40} 29" in format_report(report, identity)

    def test_unknown_model(self) -> None:
        """A device that never identified itself still formats."""

        text = format_report(_REPORT, ARDeviceIdentity())

        assert f"model     : {UNKNOWN_IDENTITY}" in text


class TestWriteProbe:
    """Tests for write_probe."""

    def test_writes_the_report(
        self, identity: ARDeviceIdentity, tmp_path: Path
    ) -> None:
        """The report lands in a file named after the device."""

        target = write_probe(_REPORT, path=tmp_path, identity=identity)

        assert target.parent == tmp_path
        assert target.suffix == ".txt"
        assert target.name.startswith("RT-AX88U_")
        assert "ARLogSource" in target.name
        assert "entries" in target.read_text(encoding="utf-8")

    def test_creates_the_directory(
        self, identity: ARDeviceIdentity, tmp_path: Path
    ) -> None:
        """A missing target directory is created."""

        target = write_probe(
            _REPORT, path=tmp_path / "deep" / "deeper", identity=identity
        )

        assert target.is_file()
