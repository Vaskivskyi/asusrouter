"""Compilers module for AsusRouter"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from asusrouter import FilterDevice
from asusrouter.const import (
    AR_MAP_RGB,
    ENDHOOKS,
    ENDPOINT,
    ENDPOINT_ARGS,
    ERRNO,
    ERROR_VALUE_TYPE,
    GWLAN,
    HOOK,
    KEY_PARENTAL_CONTROL_MAC,
    KEY_PARENTAL_CONTROL_NAME,
    KEY_PARENTAL_CONTROL_TIMEMAP,
    KEY_PARENTAL_CONTROL_TYPE,
    MAP_NVRAM,
    MAP_OVPN_STATUS,
    MAP_PARENTAL_CONTROL_TYPE,
    NVRAM_GET,
    RANGE_GWLAN,
    RANGE_OVPN_CLIENTS,
    STATE,
    STATUS,
    UNKNOWN,
    VPN,
    VPN_CLIENT,
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
        for item, value in commands:
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

    if VPN in devicemap:
        for num in RANGE_OVPN_CLIENTS:
            key = f"{VPN_CLIENT}{num}"
            if not key in vpn:
                vpn[key] = {}
            if f"{VPN_CLIENT}{num}_{STATE}" in devicemap[VPN]:
                vpn[key][STATUS] = int_from_str(
                    devicemap[VPN][f"{VPN_CLIENT}{num}_{STATE}"]
                )
                if vpn[key][STATUS] == 1 or vpn[key][STATUS] == 2:
                    vpn[key][STATE] = True
                else:
                    vpn[key][STATE] = False
                if vpn[key][STATUS] in MAP_OVPN_STATUS:
                    vpn[key][STATUS] = MAP_OVPN_STATUS[vpn[key][STATUS]]
                else:
                    vpn[key][STATUS] = f"{UNKNOWN} ({vpn[key][STATUS]})"
            if f"{VPN_CLIENT}{num}_{ERRNO}" in devicemap[VPN]:
                vpn[key][ERRNO] = int_from_str(
                    devicemap[VPN][f"{VPN_CLIENT}{num}_{ERRNO}"]
                )

    return vpn


def parental_control(data: dict[str, FilterDevice]) -> dict[str, str]:
    """Compile parental control rules"""

    if not isinstance(data, dict):
        raise AsusRouterValueError(ERROR_VALUE_TYPE.format(data, type(data)))

    types_lib = {}
    for index, state in MAP_PARENTAL_CONTROL_TYPE.items():
        types_lib[state] = index

    macs = str()
    names = str()
    types = str()
    timemaps = str()

    for rule in data:
        macs += f"{data[rule].mac}>"
        names += f"{data[rule].name}>"
        types += f"{types_lib[data[rule].type]}>"
        timemaps += f"{data[rule].timemap.replace('&#60', '<')}>"

    macs = macs[:-1]
    names = names[:-1]
    timemaps = timemaps[:-1]
    types = types[:-1]

    return {
        KEY_PARENTAL_CONTROL_MAC: macs,
        KEY_PARENTAL_CONTROL_NAME: names,
        KEY_PARENTAL_CONTROL_TIMEMAP: timemaps,
        KEY_PARENTAL_CONTROL_TYPE: types,
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

    request = []
    for intf in wlan:
        interface = WLAN_TYPE.get(intf)
        for key in MAP_NVRAM[WLAN]:
            request.append(key.value.format(interface))

        for key in MAP_NVRAM[GWLAN]:
            for gid in RANGE_GWLAN:
                request.append(key.value.format(f"{interface}.{gid}"))

    return nvram(request)
