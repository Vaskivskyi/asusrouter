"""Compilers module for AsusRouter"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from asusrouter import FilterDevice
from asusrouter.const import (
    AR_DEFAULT_OVPN_CLIENTS,
    AR_KEY_OVPN,
    AR_KEY_PARENTAL_CONTROL_MAC,
    AR_KEY_PARENTAL_CONTROL_NAME,
    AR_KEY_PARENTAL_CONTROL_STATE,
    AR_KEY_PARENTAL_CONTROL_TIMEMAP,
    AR_KEY_VPN_CLIENT,
    AR_MAP_PARENTAL_CONTROL_STATE,
    AR_MAP_RGB,
    AR_VPN_STATUS,
    ENDHOOKS,
    ENDPOINT,
    ENDPOINT_ARGS,
    ERROR_VALUE_TYPE,
    GWLAN,
    HOOK,
    KEY_VPN,
    MAP_NVRAM,
    NVRAM_GET,
    PARAM_ERRNO,
    PARAM_STATE,
    PARAM_STATUS,
    PARAM_UNKNOWN,
    RANGE_GWLAN,
    WLAN,
    WLAN_TYPE,
)
from asusrouter.dataclass import AsusDevice, ConnectedDevice
from asusrouter.error import AsusRouterValueError

from .converters import int_from_str


def hook(commands: dict[str, str] | None = None) -> str:
    """Hook compiler"""

    data = str()
    if commands is not None:
        for item, value in commands.items():
            data += f"{item}({value});"

    return data


def nvram(values: list[str] | str | None = None) -> str:
    """NVRAM compiler"""

    if values is None:
        return str()

    if isinstance(values, str):
        return f"{NVRAM_GET}({values});"

    request = str()
    for value in values:
        request += f"{NVRAM_GET}({value});"

    return request


def rgb(raw: dict[int, dict[str, int]]) -> str:
    """RGB value compiler for LEDG scheme"""

    value = str()

    raw = dict(sorted(raw.items()))

    for led in raw:
        for code in AR_MAP_RGB.values():
            if code in raw[led]:
                value += f"{raw[led][code]},"
            else:
                value += "0,"

    value = value[:-1]

    return value


def vpn_from_devicemap(
    vpn: dict[str, Any], devicemap: dict[str, Any]
) -> dict[str, Any]:
    """Compile devicemap into VPN"""

    if not isinstance(devicemap, dict):
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(devicemap, type(devicemap)))

    if not isinstance(vpn, dict):
        vpn = {}

    if KEY_VPN in devicemap:
        for num in range(1, AR_DEFAULT_OVPN_CLIENTS + 1):
            key = f"{AR_KEY_VPN_CLIENT}{num}"
            if not key in vpn:
                vpn[key] = {}
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


def parental_control(data: dict[str, FilterDevice]) -> dict[str, str]:
    """Compile parental control rules"""

    if not isinstance(data, dict):
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(data, type(data)))

    state_lib = {}
    for index, state in AR_MAP_PARENTAL_CONTROL_STATE.items():
        state_lib[state] = index

    macs = str()
    names = str()
    states = str()
    timemaps = str()

    for rule in data:
        macs += data[rule].mac + ">"
        names += data[rule].name + ">"
        states += state_lib[data[rule].state] + ">"
        timemaps += data[rule].timemap.replace("&#60", "<") + ">"

    macs = macs[:-1]
    names = names[:-1]
    states = states[:-1]
    timemaps = timemaps[:-1]

    return {
        AR_KEY_PARENTAL_CONTROL_MAC: macs,
        AR_KEY_PARENTAL_CONTROL_NAME: names,
        AR_KEY_PARENTAL_CONTROL_STATE: states,
        AR_KEY_PARENTAL_CONTROL_TIMEMAP: timemaps,
    }


def connected_device(
    device: ConnectedDevice, state: dict[str, Any] | None = None
) -> ConnectedDevice:
    """Compile connected device from different sources"""

    if state is None:
        device.online = False
        return device

    values: dict[str, Any] = asdict(device)
    values.update(state)

    return ConnectedDevice(**values)


def endpoint(endpoint: str, device: AsusDevice | dict[str, Any] | None = None) -> str:
    """Compile endpoint string with required arguments"""

    address = ENDPOINT.get(endpoint)
    if not address:
        address = ENDPOINT[HOOK] if endpoint in ENDHOOKS else str()

    if isinstance(device, AsusDevice):
        device = asdict(device)
    if not isinstance(device, dict):
        return address

    address += "?"

    if endpoint in ENDPOINT_ARGS:
        for key in ENDPOINT_ARGS[endpoint]:
            address += f"{ENDPOINT_ARGS[endpoint][key]}={device.get(key, str())}&"

    return address


def update_rec(left: dict[str, Any], right: dict[str, Any] | None = None) -> None:
    """Update dictionary with values of other dictionary"""

    if not right:
        right = {}
    for key, value in right.items():
        if key in left and isinstance(left[key], dict) and isinstance(value, dict):
            update_rec(left[key], value)
        else:
            left[key] = value


def monitor_arg_nvram(wlan: list[str] | None) -> str | None:
    """Compile NVRAM monitor"""

    if not wlan:
        return None

    request = list()
    for intf in wlan:
        interface = WLAN_TYPE.get(intf)
        for key in MAP_NVRAM[WLAN]:
            request.append(key.value.format(interface))

        for key in MAP_NVRAM[GWLAN]:
            for gid in RANGE_GWLAN:
                request.append(key.value.format(f"{interface}.{gid}"))

    return nvram(request)
