"""Probe report model for AsusRouter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from asusrouter.tools.probe.redact import scrub_text
from asusrouter.tools.security import ARSecurityLevel, render

if TYPE_CHECKING:
    from collections.abc import Iterable

# Level from which free text is shown as the device wrote it
_REVEAL_TEXT: ARSecurityLevel = ARSecurityLevel.REASONABLE


@dataclass(frozen=True, slots=True)
class ARProbeSection:
    """One titled block of label/value rows in a probe report."""

    title: str
    rows: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class ARProbeReport:
    """The result of probing one source on a live device."""

    source: str
    level: ARSecurityLevel
    sections: tuple[ARProbeSection, ...] = ()


def render_value(value: Any, level: ARSecurityLevel) -> str:
    """Render one row value for the report at `level`."""

    if isinstance(value, str):
        return value if level >= _REVEAL_TEXT else scrub_text(value)

    return str(render(value, level))


def build_section(
    title: str,
    rows: Iterable[tuple[str, Any]],
    *,
    level: ARSecurityLevel,
) -> ARProbeSection:
    """Build a section, rendering every row value at `level`."""

    return ARProbeSection(
        title,
        tuple((label, render_value(value, level)) for label, value in rows),
    )


__all__ = [
    "ARProbeReport",
    "ARProbeSection",
    "build_section",
    "render_value",
]
