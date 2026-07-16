"""Readers for ASUS JS-variable payloads."""

from __future__ import annotations

import ast
import json
import re
from typing import Any

from asusrouter.tools.converters.raw import raw_to_str

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


def read_js_section(data: Any, key: str) -> Any:
    """Read a section from JS-variable data.

    ASUS JS variables wrap their payload in a single-element list cover
    (`name = [VALUE][0];`); after parsing, the value is `[VALUE]`. Return
    its first element, or None when absent.
    """

    if not isinstance(data, dict):
        return None
    value = data.get(key)
    return value[0] if isinstance(value, list) and value else None
