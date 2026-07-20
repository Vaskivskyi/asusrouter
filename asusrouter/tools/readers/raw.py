"""Readers that parse raw device payloads into shaped data."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from asusrouter.tools.converters.raw import raw_to_bool, raw_to_str

_LOGGER = logging.getLogger(__name__)

# Control characters (NUL..TAB) that break JSON; dropped in a single pass
_STRIP_CONTROL = dict.fromkeys(range(10))

# Fixups for the malformed JSON some endpoints emit
_JSON_DOUBLE_COMMA = re.compile(r"\s*,\s*,")
_JSON_LEADING_COMMA = re.compile(r"^\s*{\s*,")
_JSON_TRAILING_COMMA = re.compile(r",\s*}\s*$")
_JSON_EMPTY_VALUE = re.compile(r":\s*(,|\})")

# Legacy firmware emits the get_clientlist value without wrapping braces,
# so its entries leak to the top level; wrap them back into an object
_JSON_CLIENTLIST = re.compile(
    r'("get_clientlist":)\s*(".*?)'
    r'(\s*,\s*"get_clientlist_from_json_database")',
    re.DOTALL,
)

# Consider a 200 with redirect meta-refresh as a bounce page, not real data
_HTML_REDIRECT = re.compile(
    r"""http-equiv\s*=\s*["']?\s*refresh""", re.IGNORECASE
)


def is_redirect_page(content: str | None) -> bool:
    """Whether the content is an HTML meta-refresh bounce, not real data."""

    text = raw_to_str(content)
    return bool(text and _HTML_REDIRECT.search(text))


def is_true_in_dict(value: str, data: dict[str, Any]) -> bool:
    """Check if the value exists in the dict and is truthy."""

    return raw_to_bool(data.get(value)) is True


def read_json_content(content: str | None) -> dict[str, Any]:
    """Get the json content, repairing the malformed JSON some devices emit."""

    content = raw_to_str(content)
    if not content:
        return {}

    # Drop control characters that break json
    content = content.translate(_STRIP_CONTROL)

    # Handle missing values in JSON
    content = _JSON_DOUBLE_COMMA.sub(", ", content)
    content = _JSON_LEADING_COMMA.sub("{", content)
    content = _JSON_TRAILING_COMMA.sub("}", content)

    # Handle keys without values
    content = _JSON_EMPTY_VALUE.sub(r": null\1", content)

    # Rewrap an unwrapped get_clientlist value
    content = _JSON_CLIENTLIST.sub(r"\1{\2}\3", content)

    try:
        json_data = json.loads(content)
        if isinstance(json_data, dict):
            return json_data
        return {}
    except json.JSONDecodeError as ex:
        _LOGGER.error(
            "Unable to decode json content with exception `%s`.\
                Please, copy this and fill in a bug report: %s",
            ex,
            content,
        )
        return {}
