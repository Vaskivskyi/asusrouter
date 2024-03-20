"""Firmware release notes endpoint module."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.data import AsusData
from asusrouter.tools.converters import clean_string


def read(content: str) -> dict[str, Any]:
    """Read firmware release note data."""

    raw_note = content.replace("\ufeff", "")
    raw_note = raw_note.replace("\uff1a", ":")  # Replace the full-width colon

    # Empty release note -> fast return
    if raw_note == "\n\n":
        return {}

    # Get only the changes
    # 1. Split the data into lines
    lines = raw_note.splitlines()
    # 2. Clean the lines
    clean_lines = []
    for line in lines:
        if "Firmware version" in line or "Release Note" in line:
            continue
        clean_line = clean_string(line)
        if clean_line:
            clean_lines.append(clean_line)
    # 3. Combine the lines into a single string again
    note = "\n".join(clean_lines)

    release_note: dict[str, Any] = {
        "release_note": note,
        "release_note_raw": raw_note,
    }

    return release_note


def process(data: dict[str, Any]) -> dict[AsusData, Any]:
    """Process firmware release note data."""

    state: dict[AsusData, Any] = {
        AsusData.FIRMWARE_NOTE: data,
    }

    return state
