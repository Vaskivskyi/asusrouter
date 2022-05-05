"""Compilers module for AsusRouter"""

from __future__ import annotations

from asusrouter.const import(
    KEY_NVRAM_GET,
)


def hook(commands : dict[str, str] | None = None) -> str:
    """"Hook compiler"""

    data = ""
    if commands is not None:
        for item in commands:
            data += "{}({});".format(item, commands[item])

    return data


def nvram(values : list[str] | str | None = None) -> str:
    """NVRAM request compiler"""

    if values is None:
        return ""

    if type(values) == str:
        return "{}({});".format(KEY_NVRAM_GET, values)

    request = ""
    for value in values:
        request += "{}({});".format(KEY_NVRAM_GET, value)

    return request


