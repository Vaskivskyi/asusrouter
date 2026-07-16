"""Readers that parse raw device payloads into shaped data."""

from __future__ import annotations

import ast
import json
import logging
import re
from typing import Any

from asusrouter.tools.converters_v2.raw import raw_to_bool, raw_to_str

_LOGGER = logging.getLogger(__name__)

# Control characters (NUL..TAB) that break JSON; dropped in a single pass
_STRIP_CONTROL = dict.fromkeys(range(10))

# A JS `name = value;` assignment (value may be a quoted string)
_JS_VAR_RE = re.compile(
    r"""(?m)                    # multiline mode
    \b                          # word boundary before variable name
    (\w+)\s*=\s*                # variable name and assignment
    (
        (?:
            "(?:[^"\\]|\\.)*"   # double-quoted string
            | '(?:[^'\\]|\\.)*' # single-quoted string
            | [^;]*?            # or anything up to semicolon
        )
    )
    \s*;                        # semicolon ends the assignment
    """,
    re.VERBOSE,
)
_ARRAY_INDEX_RE = re.compile(r"\[\d+\]")

# Fixups for the malformed JSON some endpoints emit
_JSON_DOUBLE_COMMA = re.compile(r"\s*,\s*,")
_JSON_LEADING_COMMA = re.compile(r"^\s*{\s*,")
_JSON_TRAILING_COMMA = re.compile(r",\s*}\s*$")
_JSON_EMPTY_VALUE = re.compile(r":\s*(,|\})")


def is_true_in_dict(value: str, data: dict[str, Any]) -> bool:
    """Check if the value exists in the dict and is truthy."""

    return raw_to_bool(data.get(value)) is True


def read_js_variables(content: str) -> dict[str, Any]:
    """Get all the JS variables from the content."""

    content = raw_to_str(content) or ""
    js_variables: dict[str, Any] = {}

    for match in _JS_VAR_RE.finditer(content):
        key, value = match.groups()

        # Clean value from the array indexes
        value = _ARRAY_INDEX_RE.sub("", value)

        # Try JSON
        try:
            js_variables[key] = json.loads(value)
            continue
        except json.JSONDecodeError:
            pass
        # Try python literal eval
        try:
            js_variables[key] = ast.literal_eval(value)
            continue
        except (ValueError, SyntaxError):
            pass
        # Clean the value of quotes if it starts and ends with them
        if (value.startswith("'") and value.endswith("'")) or (
            value.startswith('"') and value.endswith('"')
        ):
            value = value[1:-1]
        js_variables[key] = value

    return js_variables


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
