"""Reading tools for AsusRouter."""

from __future__ import annotations

from asusrouter.tools.readers.js import read_js_section, read_js_variables
from asusrouter.tools.readers.netdev import read_netdev
from asusrouter.tools.readers.nvram_list import decode, get_field, split_rows
from asusrouter.tools.readers.raw import (
    is_redirect_page,
    is_true_in_dict,
    read_json_content,
)
from asusrouter.tools.readers.table import read_table

__all__ = [
    "decode",
    "get_field",
    "is_redirect_page",
    "is_true_in_dict",
    "read_js_section",
    "read_js_variables",
    "read_json_content",
    "read_netdev",
    "read_table",
    "split_rows",
]
