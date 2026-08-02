"""Disk writer for AsusRouter probe reports."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import re
from typing import TYPE_CHECKING, Final

from asusrouter.const import __version__

if TYPE_CHECKING:
    from asusrouter.modules.device.identity import ARDeviceIdentity
    from asusrouter.tools.probe.report import ARProbeReport

# Default root for written reports
DEFAULT_PROBE_PATH: Final[str] = "probes"

# Emitted once per session before the first probe
PROBE_SENSITIVE_WARNING: Final[str] = (
    "Probe reports are redacted on a best-effort basis only: message "
    "bodies are free text, so an SSID, a hostname or a serial can "
    "survive the scrubbing. Read a report before sharing it"
)

# Path token for an incomplete identity
UNKNOWN_IDENTITY: Final[str] = "unknown"

# Width the row labels are padded to
_LABEL_WIDTH: Final[int] = 26

_UNSAFE_PATH = re.compile(r"[^A-Za-z0-9._-]+")


def _path_token(value: str | None) -> str:
    """Reduce a value to a token safe to put in a file name."""

    token = _UNSAFE_PATH.sub("_", value or "").strip("_")

    return token or UNKNOWN_IDENTITY


def format_report(report: ARProbeReport, identity: ARDeviceIdentity) -> str:
    """Render a report as the text a user can read or attach to a report."""

    lines = [
        "AsusRouter probe report",
        "=======================",
        "",
        f"generated : {datetime.now(UTC).isoformat()}",
        f"library   : {__version__}",
        f"model     : {identity.model or UNKNOWN_IDENTITY}",
        f"firmware  : {identity.firmware}",
        f"source    : {report.source}",
        f"security  : {report.level.name}",
        "",
        PROBE_SENSITIVE_WARNING,
    ]

    for section in report.sections:
        lines.append("")
        lines.append(
            f"--- {section.title} " + "-" * max(0, 74 - len(section.title))
        )
        # A label wider than the column still keeps a separator
        lines.extend(
            f"{label.ljust(_LABEL_WIDTH)} {value}"
            for label, value in section.rows
        )

    return "\n".join(lines) + "\n"


def write_probe(
    report: ARProbeReport,
    *,
    path: str | Path,
    identity: ARDeviceIdentity,
) -> Path:
    """Write a report to `{path}/{model}_{firmware}_{source}_{stamp}.txt`."""

    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    name = "_".join(
        (
            _path_token(identity.model),
            _path_token(str(identity.firmware)),
            _path_token(report.source),
            stamp,
        )
    )

    target = directory / f"{name}.txt"
    target.write_text(format_report(report, identity), encoding="utf-8")

    return target


__all__ = [
    "DEFAULT_PROBE_PATH",
    "PROBE_SENSITIVE_WARNING",
    "UNKNOWN_IDENTITY",
    "format_report",
    "write_probe",
]
