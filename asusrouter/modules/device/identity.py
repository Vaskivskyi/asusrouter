"""Device identity module for AsusRouter."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from asusrouter.modules.firmware import Firmware
from asusrouter.modules.nvram import ARNvramType
from asusrouter.modules.support import ARSupportSourceUniversal
from asusrouter.modules.support.flag import ARSupportType
from asusrouter.modules.wifi import ARWiFiBand
from asusrouter.tools.converters import clean_string, safe_list_from_string
from asusrouter.tools.identifiers import MacAddress

IdentityData = Mapping[Any, Any]


# TODO: Redo this legacy part
def _translate_firmware(data: IdentityData) -> Firmware:
    """Build firmware information from raw data."""

    firmware = Firmware()
    firmware.from_string(
        f"{data.get(ARNvramType.FW_MAJOR, '')}."
        f"{data.get(ARNvramType.FW_MINOR, '')}."
        f"{data.get(ARNvramType.FW_BUILD, '')}"
    )
    return firmware


# TODO: Redo this part
def _translate_wifi(data: IdentityData) -> dict[ARWiFiBand, int]:
    """Parse WiFi support data from the raw device payload."""

    support_data = data.get(ARSupportSourceUniversal)
    if not isinstance(support_data, dict):
        support_data = {}

    bands = safe_list_from_string(
        data.get(ARNvramType.WIRELESS_BANDS, ""), "&#60"
    )
    bands_ids = support_data.get(ARSupportType.WIFI_UNITS, ())

    result: dict[ARWiFiBand, int] = {}
    for band, band_id in zip(bands, bands_ids):
        try:
            band_enum = ARWiFiBand(band)
            result[band_enum] = band_id
        except ValueError:
            continue

    return result


def _translate_base_identity(
    data: IdentityData,
) -> tuple[MacAddress | None, str | None, str | None, str | None]:
    return (
        MacAddress.from_value_safe(data.get(ARNvramType.MAC)),
        clean_string(data.get(ARNvramType.MODEL)),
        clean_string(data.get(ARNvramType.MODEL_ORIGINAL)),
        clean_string(data.get(ARNvramType.SERIAL)),
    )


class ARDeviceIdentity:
    """AsusRouter device identity class."""

    def __init__(self) -> None:
        """Initialize the device identity."""

        self._brand: str = "ASUSTek"
        self._firmware: Firmware | None = None
        self._mac: MacAddress | None = None
        self._model: str | None = None
        self._model_original: str | None = None
        self._serial: str | None = None
        self._wifi: dict[ARWiFiBand, int] = {}

    @property
    def brand(self) -> str:
        """Get the brand."""

        return self._brand

    @property
    def firmware(self) -> Firmware | None:
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
    def wifi(self) -> dict[ARWiFiBand, int]:
        """Get the WiFi information."""

        return self._wifi

    @classmethod
    def build(cls, data: IdentityData) -> ARDeviceIdentity:
        """Build the device identity from the data."""

        identity = cls()
        identity._firmware = _translate_firmware(data)
        (
            identity._mac,
            identity._model,
            identity._model_original,
            identity._serial,
        ) = _translate_base_identity(data)
        identity._wifi = _translate_wifi(data)

        return identity
