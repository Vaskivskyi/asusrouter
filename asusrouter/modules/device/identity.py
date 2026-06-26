"""Device identity module for AsusRouter."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from asusrouter.const import DEFAULT_IDENTITY_BRAND
from asusrouter.modules.aimesh.topology import ARAiMeshTopology
from asusrouter.modules.firmware import ARFirmware
from asusrouter.modules.nvram import ARNvramType
from asusrouter.modules.support import ARSupportSourceUniversal
from asusrouter.modules.support.flag import ARSupportType
from asusrouter.modules.wifi import ARWiFiBand
from asusrouter.tools.converters import safe_list_from_string
from asusrouter.tools.converters_v2.raw import raw_to_str
from asusrouter.tools.identifiers import MacAddress

IdentityData = Mapping[Any, Any]


def _translate_firmware(data: IdentityData) -> ARFirmware:
    """Build firmware information from raw data."""

    return ARFirmware.from_nvram(
        data.get(ARNvramType.FW_MAJOR),
        data.get(ARNvramType.FW_MINOR),
        data.get(ARNvramType.FW_BUILD),
    )


# TODO: Redo this part
def _translate_wifi(
    data: IdentityData, support: dict[ARSupportType, Any]
) -> dict[ARWiFiBand, int]:
    """Parse WiFi support data from the raw device payload."""

    bands = safe_list_from_string(
        data.get(ARNvramType.WIRELESS_BANDS, ""), "&#60"
    )
    bands_ids = support.get(ARSupportType.WIFI_UNITS, ())

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


def _translate_identity_base(
    data: IdentityData,
) -> tuple[MacAddress | None, str | None, str | None, str | None]:
    """Parse the base identity information from the raw payload."""

    return (
        MacAddress.from_value_safe(data.get(ARNvramType.MAC)),
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
        self._serial: str | None = None
        self._support: dict[ARSupportType, Any] = {}
        self._wifi: dict[ARWiFiBand, int] = {}
        # Live AiMesh topology - the only mutable identity part, swapped
        # atomically as a whole snapshot by `update_aimesh`
        self._aimesh: ARAiMeshTopology = ARAiMeshTopology()
        # Live boot time - the stabilization anchor; seeded or fetched and
        # kept in sync by `update_boottime`
        self._boottime: datetime | None = None

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
    def aimesh(self) -> ARAiMeshTopology:
        """Get the live AiMesh topology."""

        return self._aimesh

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
        identity._wifi = _translate_wifi(data, identity._support)

        return identity
