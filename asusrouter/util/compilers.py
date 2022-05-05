"""Compilers module for AsusRouter"""

from __future__ import annotations

from asusrouter.const import(
    AR_HOOK_TEMPLATE,
    KEY_NVRAM_GET,
)


def hook(commands : dict[str, str] | None = None) -> str:
    """"Hook compiler"""

    data = str()
    if commands is not None:
        for item in commands:
            data += AR_HOOK_TEMPLATE.format(item, commands[item])

    return data


def nvram(values : list[str] | str | None = None) -> str:
    """NVRAM request compiler"""

    if values is None:
        return str()

    if type(values) == str:
        return AR_HOOK_TEMPLATE.format(KEY_NVRAM_GET, values)

    request = str()
    for value in values:
        request += AR_HOOK_TEMPLATE.format(KEY_NVRAM_GET, value)

    return request


