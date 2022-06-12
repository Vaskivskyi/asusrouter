"""Compilers module for AsusRouter"""

from __future__ import annotations
from typing import Any

from asusrouter.const import (
    AR_DEFAULT_OVPN_CLIENTS,
    AR_HOOK_TEMPLATE,
    AR_KEY_OVPN,
    AR_KEY_VPN_CLIENT,
    AR_MAP_RGB,
    AR_VPN_STATUS,
    ERROR_VALUE_TYPE,
    KEY_NVRAM_GET,
    KEY_VPN,
    PARAM_ERRNO,
    PARAM_STATE,
    PARAM_STATUS,
    PARAM_UNKNOWN,
)
from asusrouter.error import AsusRouterValueError
from .converters import int_from_str


def hook(commands: dict[str, str] | None = None) -> str:
    """Hook compiler"""

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


def vpn_from_devicemap(
    vpn: dict[str, Any], devicemap: dict[str, Any]
) -> dict[str, Any]:
    """Compile devicemap into VPN"""

    if type(devicemap) != dict:
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(devicemap, type(devicemap)))

    if type(vpn) != dict:
        vpn = dict()

    if KEY_VPN in devicemap:
        for num in range(1, AR_DEFAULT_OVPN_CLIENTS + 1):
            key = f"{AR_KEY_VPN_CLIENT}{num}"
            if not key in vpn:
                vpn[key] = dict()
            if (
                AR_KEY_OVPN.format(AR_KEY_VPN_CLIENT, num, PARAM_STATE)
                in devicemap[KEY_VPN]
            ):
                vpn[key][PARAM_STATUS] = int_from_str(
                    devicemap[KEY_VPN][
                        AR_KEY_OVPN.format(AR_KEY_VPN_CLIENT, num, PARAM_STATE)
                    ]
                )
                if vpn[key][PARAM_STATUS] == 1 or vpn[key][PARAM_STATUS] == 2:
                    vpn[key][PARAM_STATE] = True
                else:
                    vpn[key][PARAM_STATE] = False
                if vpn[key][PARAM_STATUS] in AR_VPN_STATUS:
                    vpn[key][PARAM_STATUS] = AR_VPN_STATUS[vpn[key][PARAM_STATUS]]
                else:
                    vpn[key][
                        PARAM_STATUS
                    ] = f"{PARAM_UNKNOWN} ({vpn[key][PARAM_STATUS]})"
            if (
                AR_KEY_OVPN.format(AR_KEY_VPN_CLIENT, num, PARAM_ERRNO)
                in devicemap[KEY_VPN]
            ):
                vpn[key][PARAM_ERRNO] = int_from_str(
                    devicemap[KEY_VPN][
                        AR_KEY_OVPN.format(AR_KEY_VPN_CLIENT, num, PARAM_ERRNO)
                    ]
                )

    return vpn
