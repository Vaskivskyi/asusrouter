"""Writers module.

This module contains the writers for AsusRouter, which prepare data to be sent to the router."""


from __future__ import annotations

from asusrouter.tools.converters import clean_input


@clean_input
def nvram(content: str | list[str] | None = None) -> str | None:
    """NVRAM writer.

    This function converts a list of strings (or a single string)
    into a string request to the NVRAM read endpoint."""

    if isinstance(content, str):
        return f"nvram_get({content});"

    if isinstance(content, list):
        return "".join([f"nvram_get({item});" for item in content])

    return None
