"""Readers for `<`-row / `>`-field encoded NVRAM lists."""

from __future__ import annotations

from typing import Any


def decode(raw: Any) -> str:
    """Decode the char-encoded nvram separators to `<`/`>`."""

    if not isinstance(raw, str):
        return ""
    return raw.replace("&#60", "<").replace("&#62", ">")


def split_rows(raw: Any) -> list[str]:
    """Decode a nvram list and split it into its `<`-delimited rows.

    Rows are kept verbatim (including empty ones), so positional lists
    stay aligned and can be re-serialized without loss.
    """

    text = decode(raw)
    return text.split("<") if text else []


def get_field(parts: list[str], index: int) -> str | None:
    """Return a `>`-split field, or None when absent."""

    return parts[index] if 0 <= index < len(parts) else None
