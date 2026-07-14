"""Converters module.

This module has methods to convert data between different formats
without complicated logic. In case data cannot be converted,
`None` is returned and no exception is raised.

If data conversion requires complicated logic,
it should be in the Readers module
"""

from __future__ import annotations

from datetime import datetime

from asusrouter.tools.converters_v2.raw import raw_to_str


def safe_datetime(content: str | None) -> datetime | None:
    """Read the content as datetime or return None."""

    content = raw_to_str(content)
    if not content:
        return None

    try:
        return datetime.fromisoformat(content)
    except (ValueError, TypeError):
        try:
            return datetime.strptime(content, "%a, %d %b %Y %H:%M:%S %z")
        except (ValueError, TypeError):
            return None


def safe_list_from_string(
    content: str | None, delimiter: str = " "
) -> list[str]:
    """Read the content as list or return empty list."""

    content = raw_to_str(content)
    if not isinstance(content, str):
        return []

    return content.split(delimiter)
