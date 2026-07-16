"""Firmware release note reader."""

from __future__ import annotations

from asusrouter.tools.converters.raw import _BOM, raw_to_str

# Header lines that are not part of the actual change list
_NOTE_HEADERS = ("Firmware version", "Release Note")


def read_firmware_note(content: str) -> str | None:
    """Parse a firmware release note into cleaned change text.

    Strips the BOM and the header lines, keeping only the change lines.
    Returns None for an empty note.
    """

    raw_note = content.replace(_BOM, "")

    clean_lines = [
        line
        for raw_line in raw_note.splitlines()
        if (line := raw_to_str(raw_line))
        and not any(header in line for header in _NOTE_HEADERS)
    ]

    return "\n".join(clean_lines) or None
