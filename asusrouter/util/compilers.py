"""Compilers module for AsusRouter"""

from __future__ import annotations

from asusrouter.const import AR_HOOK_TEMPLATE, AR_MAP_RGB, KEY_NVRAM_GET


def hook(commands: dict[str, str] | None = None) -> str:
    """ "Hook compiler"""

    data = str()
    if commands is not None:
        for item in commands:
            data += AR_HOOK_TEMPLATE.format(item, commands[item])

    return data


def nvram(values: list[str] | str | None = None) -> str:
    """NVRAM request compiler"""

    if values is None:
        return str()

    if type(values) == str:
        return AR_HOOK_TEMPLATE.format(KEY_NVRAM_GET, values)

    request = str()
    for value in values:
        request += AR_HOOK_TEMPLATE.format(KEY_NVRAM_GET, value)

    return request


def rgb(raw: dict[int, dict[str, int]]) -> str:
    """RGB value compiler for LEDG scheme"""

    value = str()

    raw = dict(sorted(raw.items()))

    for led in raw:
        for channel in AR_MAP_RGB:
            if AR_MAP_RGB[channel] in raw[led]:
                value += f"{raw[led][AR_MAP_RGB[channel]]},"
            else:
                value += "0,"

    value = value[:-1]

    return value
