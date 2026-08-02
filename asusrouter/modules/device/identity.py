"""Device identity module for AsusRouter."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from asusrouter.const import DEFAULT_IDENTITY_BRAND
from asusrouter.modules.aimesh.topology import ARAiMeshTopology
from asusrouter.modules.common.device import AROperationMode
from asusrouter.modules.device.recovery import recover_support
from asusrouter.modules.firmware import ARFirmware
from asusrouter.modules.nvram import (
    ARNvramIndexSource,
    ARNvramIndexType,
    ARNvramType,
)
from asusrouter.modules.support import ARSupportSourceUniversal
from asusrouter.modules.support.flag import ARSupportType
from asusrouter.modules.wifi import (
    AR_WIFI_MAX_UNITS,
    ARWiFiBand,
    ARWiFiCapability,
)
from asusrouter.tools.converters.raw import raw_to_int, raw_to_str
from asusrouter.tools.identifiers import MacAddress, Username
from asusrouter.tools.readers import split_rows

IdentityData = Mapping[Any, Any]


def _translate_firmware(data: IdentityData) -> ARFirmware:
    """Build firmware information from raw data."""

    return ARFirmware.from_nvram(
        data.get(ARNvramType.FW_MAJOR),
        data.get(ARNvramType.FW_MINOR),
        data.get(ARNvramType.FW_BUILD),
    )


def _wifi_from_bands(
    data: IdentityData, support: dict[ARSupportType, Any]
) -> dict[ARWiFiBand, int]:
    """Map bands via `WIRELESS_BANDS` nvram and the WiFi units support."""

    bands = split_rows(data.get(ARNvramType.WIRELESS_BANDS))
    capabilities = support.get(ARSupportType.WIFI_CAPABILITIES, {})
    bands_ids = capabilities.get(ARWiFiCapability.UNITS, ())

    result: dict[ARWiFiBand, int] = {}
    for band, band_id in zip(bands, bands_ids):
        try:
            band_enum = ARWiFiBand(band)
        except ValueError:
            continue
        if band_enum is ARWiFiBand.UNKNOWN:
            continue
        result[band_enum] = band_id

    return result


def _wifi_from_nband(data: IdentityData) -> dict[ARWiFiBand, int]:
    """Derive bands from per-radio `wl{}_nband` (older firmware fallback)."""

    result: dict[ARWiFiBand, int] = {}
    for unit in range(AR_WIFI_MAX_UNITS):
        band = ARWiFiBand.from_nband(
            raw_to_str(
                data.get(ARNvramIndexSource(ARNvramIndexType.WL_NBAND, unit))
            )
        )
        if band is not ARWiFiBand.UNKNOWN and band not in result:
            result[band] = unit

    return result


def _translate_wifi(
    data: IdentityData, support: dict[ARSupportType, Any]
) -> dict[ARWiFiBand, int]:
    """Parse the WiFi band -> unit map from the raw device payload."""

    return _wifi_from_bands(data, support) or _wifi_from_nband(data)


def _translate_mac(data: IdentityData) -> MacAddress | None:
    """Pick the device MAC, falling back when the label MAC is blank."""

    for key in (ARNvramType.MAC, ARNvramType.MAC_LAN, ARNvramType.MAC_WAN):
        mac = MacAddress.from_value_safe(data.get(key))
        if mac is not None:
            return mac
    return None


# Proxy-STA (`wlc_psta`) states that refine an AP/repeater `sw_mode`
_PSTA_BRIDGE = 1  # media bridge over a repeater or AP base
_PSTA_REPEATER = 2  # repeater over an AP base
_PSTA_BRIDGE_ON_AP = 3  # media bridge over an AP base

_RE_MODE_AIMESH_NODE = 1  # `re_mode` value marking an AiMesh node


def _translate_operation_mode(data: IdentityData) -> AROperationMode:
    """Resolve the active operation mode from `sw_mode` and `wlc_psta`."""

    if raw_to_int(data.get(ARNvramType.RE_MODE)) == _RE_MODE_AIMESH_NODE:
        return AROperationMode.AIMESH_NODE

    sw_mode = raw_to_int(data.get(ARNvramType.SW_MODE))
    mode = AROperationMode.from_value(sw_mode)
    psta = raw_to_int(data.get(ARNvramType.WLC_PROXY_STA))

    repeater_or_ap = (AROperationMode.REPEATER, AROperationMode.ACCESS_POINT)
    if (mode in repeater_or_ap and psta == _PSTA_BRIDGE) or (
        mode is AROperationMode.ACCESS_POINT and psta == _PSTA_BRIDGE_ON_AP
    ):
        return AROperationMode.MEDIA_BRIDGE
    if mode is AROperationMode.ACCESS_POINT and psta == _PSTA_REPEATER:
        return AROperationMode.REPEATER
    return mode


def _translate_identity_base(
    data: IdentityData,
) -> tuple[MacAddress | None, str | None, str | None, str | None]:
    """Parse the base identity information from the raw payload."""

    return (
        _translate_mac(data),
        raw_to_str(data.get(ARNvramType.MODEL)),
        raw_to_str(data.get(ARNvramType.MODEL_ORIGINAL)),
        raw_to_str(data.get(ARNvramType.SERIAL)),
    )


class ARDeviceIdentity:
    """AsusRouter device identity class."""

    def __init__(self) -> None:
        """Initialize the device identity."""

        self._brand: str = DEFAULT_IDENTITY_BRAND
        self._firmware: ARFirmware = ARFirmware()
        self._mac: MacAddress | None = None
        self._model: str | None = None
        self._model_original: str | None = None
        self._operation_mode: AROperationMode = AROperationMode.UNKNOWN
        self._serial: str | None = None
        self._support: dict[ARSupportType, Any] = {}
        # Login name used to reach the device - injected
        self._username: Username | None = None
        self._wifi: dict[ARWiFiBand, int] = {}
        # Live AiMesh topology - the only mutable identity part, swapped
        # atomically as a whole snapshot by `update_aimesh`
        self._aimesh: ARAiMeshTopology = ARAiMeshTopology()
        # Live boot time - the stabilization anchor; seeded or fetched and
        # kept in sync by `update_boottime`
        self._boottime: datetime | None = None
        # Seconds the device has been running
        self._uptime: int | None = None
        # The device's own clock as of the last read
        self._device_time: datetime | None = None
        # Edge flag - set when the uptime falls back (a reboot)
        self._rebooted: bool = False

    @property
    def brand(self) -> str:
        """Get the brand."""

        return self._brand

    @property
    def firmware(self) -> ARFirmware:
        """Get the firmware information."""

        return self._firmware

    @property
    def mac(self) -> MacAddress | None:
        """Get the MAC address."""

        return self._mac

    @property
    def model(self) -> str | None:
        """Get the model."""

        return self._model

    @property
    def model_original(self) -> str | None:
        """Get the original model."""

        return self._model_original

    @property
    def operation_mode(self) -> AROperationMode:
        """Get the active operation mode."""

        return self._operation_mode

    @property
    def serial(self) -> str | None:
        """Get the serial number."""

        return self._serial

    @property
    def support(self) -> dict[ARSupportType, Any]:
        """Get the support information."""

        return self._support

    @property
    def wifi(self) -> dict[ARWiFiBand, int]:
        """Get the WiFi information."""

        return self._wifi

    @property
    def wifi_by_unit(self) -> dict[int, ARWiFiBand]:
        """Map a wireless unit index to its band."""

        return {unit: band for band, unit in self._wifi.items()}

    @property
    def aimesh(self) -> ARAiMeshTopology:
        """Get the live AiMesh topology."""

        return self._aimesh

    @property
    def username(self) -> Username | None:
        """Get the login name used to reach the device."""

        return self._username

    def update_username(self, username: Username | None) -> None:
        """Set the login name used to reach the device."""

        self._username = username

    def update_aimesh(self, topology: ARAiMeshTopology) -> None:
        """Replace the AiMesh topology snapshot atomically."""

        self._aimesh = topology

    @property
    def boottime(self) -> datetime | None:
        """Get the live boot time."""

        return self._boottime

    def update_boottime(self, boottime: datetime | None) -> None:
        """Replace the boot time."""

        self._boottime = boottime

    @property
    def uptime(self) -> int | None:
        """Get the seconds the device has been running."""

        return self._uptime

    def update_uptime(self, uptime: int | None) -> None:
        """Replace the uptime, flagging a reboot when it falls back."""

        previous = self._uptime
        self._uptime = uptime
        if previous is not None and uptime is not None and uptime < previous:
            self._rebooted = True

    @property
    def device_time(self) -> datetime | None:
        """Get the device's own clock as of the last read."""

        return self._device_time

    def update_device_time(self, device_time: datetime | None) -> None:
        """Replace the device's own clock."""

        self._device_time = device_time

    @property
    def rebooted(self) -> bool:
        """Whether a reboot was detected since it was last cleared."""

        return self._rebooted

    def mark_reboot(self) -> None:
        """Flag a reboot triggered by an action, before the boot time moves."""

        self._rebooted = True

    def clear_rebooted(self) -> None:
        """Clear the reboot flag after it has been acted upon."""

        self._rebooted = False

    @classmethod
    def build(cls, data: IdentityData) -> ARDeviceIdentity:
        """Build the device identity from the data."""

        identity = cls()
        support = data.get(ARSupportSourceUniversal)
        identity._support = support if isinstance(support, dict) else {}
        identity._firmware = _translate_firmware(data)
        (
            identity._mac,
            identity._model,
            identity._model_original,
            identity._serial,
        ) = _translate_identity_base(data)
        identity._operation_mode = _translate_operation_mode(data)
        identity._wifi = _translate_wifi(data, identity._support)

        # Try to recover missing values indirectly
        recover_support(identity)

        return identity
