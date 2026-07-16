"""Endpoint-specific content translators.

Readers that are tied to a single endpoint and are not meant to be
reused elsewhere live here, next to the endpoint definitions.
"""

from __future__ import annotations

from typing import Any

from asusrouter.tools.converters.raw import raw_to_str
from asusrouter.tools.readers import read_json_content


def read_wan_lan_status(content: str, **kwargs: Any) -> dict[str, Any]:
    """Read the wan/lan port status content.

    The endpoint wraps the JSON in a `get_wan_lan_status = {...};`
    assignment, so the prefix and trailing semicolon are stripped first.
    """

    content = raw_to_str(content) or ""
    content = content.replace("get_wan_lan_status = ", "").replace(";", "")

    return read_json_content(content)
