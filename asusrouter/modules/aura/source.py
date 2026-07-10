"""Aura data source for AsusRouter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from asusrouter.modules.aura.enums import (
    AURA_COLOR_SCHEMES,
    ARAuraField,
    ARAuraScheme,
)
from asusrouter.modules.aura.support import (
    aura_supported,
    night_mode_supported,
)
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.endpoint_v2.hooks import ARHook, hook_request
from asusrouter.modules.nvram import ARNvramType
from asusrouter.modules.source import ARDataSource
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.color import COLOR_SCALE_ASUS_DAY, Color, parse_colors
from asusrouter.tools.converters_v2.raw import raw_to_bool, raw_to_int
from asusrouter.tools.types import ARCallbackType

if TYPE_CHECKING:
    from asusrouter.modules.device.identity import ARDeviceIdentity

# Scheme codes that carry stored colors in nvram
_SCHEME_CODES = range(8)

_DAY_COLOR_KEYS = [
    f"{ARNvramType.AURA_RGB.value}{code}" for code in _SCHEME_CODES
]
_SCALAR_KEYS = [
    ARNvramType.AURA.value,
    ARNvramType.AURA_SCHEME.value,
    ARNvramType.AURA_SCHEME_PREV.value,
    ARNvramType.AURA_COUNT.value,
    ARNvramType.AURA_NIGHT_MODE.value,
]
_ALL_KEYS = _SCALAR_KEYS + _DAY_COLOR_KEYS


class ARAuraSource(ARDataSource):
    """AsusRouter Aura light effect data source."""


# Universal instance - preferred
ARAuraSourceUniversal: ARAuraSource = ARAuraSource()


async def get_state(
    callback: ARCallbackType,
    source: ARAuraSource,
    *,
    identity: ARDeviceIdentity | None = None,
    **kwargs: Any,
) -> Any:
    """Fetch the Aura nvram configuration."""

    if not aura_supported(identity):
        return {}

    request = hook_request(*((ARHook.NVRAM_GET, key) for key in _ALL_KEYS))
    return await callback(endpoint=AREndpoint.FETCH_DATA, request=request)


def _parse_scheme_colors(
    data: dict[str, Any], prefix: str, scale: int
) -> dict[ARAuraScheme, list[Color]]:
    """Parse per-scheme colors from `<prefix><code>` nvram keys."""

    colors: dict[ARAuraScheme, list[Color]] = {}
    for code in _SCHEME_CODES:
        parsed = parse_colors(data.get(f"{prefix}{code}"), scale=scale)
        if parsed:
            colors[ARAuraScheme(code)] = parsed

    return colors


def translate_state(
    data: Any,
    *,
    identity: ARDeviceIdentity | None = None,
    **kwargs: Any,
) -> dict[ARAuraField, Any]:
    """Translate raw Aura nvram into a structured dict."""

    if not isinstance(data, dict) or not data:
        return {}

    scheme = ARAuraScheme.from_value(data.get(ARNvramType.AURA_SCHEME.value))
    scheme_prev = ARAuraScheme.from_value(
        data.get(ARNvramType.AURA_SCHEME_PREV.value)
    )

    state = raw_to_bool(data.get(ARNvramType.AURA.value)) or False
    if scheme is ARAuraScheme.OFF:
        state = False

    day_colors = _parse_scheme_colors(
        data, ARNvramType.AURA_RGB.value, COLOR_SCALE_ASUS_DAY
    )

    zones = raw_to_int(data.get(ARNvramType.AURA_COUNT.value))
    if not zones:
        zones = len(day_colors.get(ARAuraScheme.STATIC, []))

    result: dict[ARAuraField, Any] = {
        ARAuraField.STATE: state,
        ARAuraField.SCHEME: scheme,
        ARAuraField.SCHEME_PREV: scheme_prev,
        ARAuraField.ZONES: zones,
        ARAuraField.COLORS: day_colors,
    }

    if night_mode_supported(identity):
        result[ARAuraField.NIGHT_MODE] = (
            raw_to_bool(data.get(ARNvramType.AURA_NIGHT_MODE.value)) or False
        )

    # Active scheme summary
    active = day_colors.get(scheme) if scheme in AURA_COLOR_SCHEMES else None
    if active:
        result[ARAuraField.COLOR] = Color.blend(active)
        result[ARAuraField.BRIGHTNESS] = max(
            color.brightness for color in active
        )

    return result


ARCallReg.register_module(
    ARAuraSource, get_state=get_state, translate_state=translate_state
)


__all__ = [
    "ARAuraSource",
    "ARAuraSourceUniversal",
    "get_state",
    "translate_state",
]
