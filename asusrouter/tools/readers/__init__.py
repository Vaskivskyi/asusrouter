"""Reading tools for AsusRouter."""

from __future__ import annotations

from asusrouter.tools.readers.js import read_js_section, read_js_variables
from asusrouter.tools.readers.netdev import read_netdev
from asusrouter.tools.readers.raw import is_true_in_dict, read_json_content

__all__ = [
    "is_true_in_dict",
    "read_js_section",
    "read_js_variables",
    "read_json_content",
    "read_netdev",
]
