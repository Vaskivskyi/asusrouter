"""LED data source for AsusRouter."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from asusrouter.modules.led.enums import ARLedField
from asusrouter.modules.nvram import ARNvramType, async_fetch_values
from asusrouter.modules.source import ARDataSource
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.converters.raw import raw_to_bool
from asusrouter.tools.types import ARCallbackType

if TYPE_CHECKING:
    from asusrouter.modules.device.identity import ARDeviceIdentity


class ARLedSource(ARDataSource):
    """AsusRouter LED data source."""


# Universal instance - preferred
ARLedSourceUniversal: ARLedSource = ARLedSource()


async def get_state(
    callback: ARCallbackType,
    source: ARLedSource,
    *,
    get_data_callback: ARCallbackType | None = None,
    identity: ARDeviceIdentity | None = None,
    **kwargs: Any,
) -> dict[Any, Any]:
    """Fetch the LED state through the NVRAM module."""

    return await async_fetch_values(get_data_callback, LED_REQUEST)


# Translation map: nvram key -> field, converter
_TRANSLATION: tuple[
    tuple[ARNvramType, ARLedField, Callable[[Any], Any]], ...
] = ((ARNvramType.LED, ARLedField.STATE, raw_to_bool),)

# Full NVRAM request for the LED state, built once
LED_REQUEST: tuple[ARNvramType, ...] = tuple(key for key, _, _ in _TRANSLATION)


def translate_state(
    data: Any,
    *,
    identity: ARDeviceIdentity | None = None,
    **kwargs: Any,
) -> dict[ARLedField, Any]:
    """Translate raw LED nvram into a structured dict."""

    if not isinstance(data, dict) or not data:
        return {}

    return {
        field: convert(data.get(key)) for key, field, convert in _TRANSLATION
    }


ARCallReg.register_module(
    ARLedSource,
    get_state=get_state,
    translate_state=translate_state,
)


__all__ = [
    "ARLedSource",
    "ARLedSourceUniversal",
    "LED_REQUEST",
    "get_state",
    "translate_state",
]
