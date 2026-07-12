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
from asusrouter.modules.nvram import (
    ARNvramIndexSource,
    ARNvramIndexType,
    ARNvramItem,
    ARNvramType,
)
from asusrouter.modules.source import ARDataSource
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.color import COLOR_SCALE_ASUS_DAY, Color, parse_colors
from asusrouter.tools.converters_v2.raw import raw_to_bool, raw_to_int
from asusrouter.tools.types import ARCallbackType

if TYPE_CHECKING:
    from asusrouter.modules.device.identity import ARDeviceIdentity

# Scheme codes that carry stored colors in nvram
_SCHEME_CODES = range(8)

# Per-scheme day color sources (`ledg_rgb<code>`)
_COLOR_SOURCES: tuple[ARNvramIndexSource, ...] = tuple(
    ARNvramIndexSource(ARNvramIndexType.AURA_RGB, code)
    for code in _SCHEME_CODES
)

# Full NVRAM request for the Aura state, built once
_AURA_REQUEST: tuple[ARNvramItem, ...] = (
    ARNvramType.AURA,
    ARNvramType.AURA_SCHEME,
    ARNvramType.AURA_SCHEME_PREV,
    ARNvramType.AURA_COUNT,
    ARNvramType.AURA_NIGHT_MODE,
    *_COLOR_SOURCES,
)


class ARAuraSource(ARDataSource):
    """AsusRouter Aura light effect data source."""


# Universal instance - preferred
ARAuraSourceUniversal: ARAuraSource = ARAuraSource()


async def get_state(
    callback: ARCallbackType,
    source: ARAuraSource,
    *,
    get_data_callback: ARCallbackType | None = None,
    identity: ARDeviceIdentity | None = None,
    **kwargs: Any,
) -> dict[Any, Any]:
    """Fetch the Aura configuration through the NVRAM module."""

    if not aura_supported(identity) or get_data_callback is None:
        return {}

    values = await get_data_callback(_AURA_REQUEST)
    return values if isinstance(values, dict) else {}


def _parse_scheme_colors(
    data: dict[Any, Any], scale: int
) -> dict[ARAuraScheme, list[Color]]:
    """Parse per-scheme colors from the indexed color sources."""

    colors: dict[ARAuraScheme, list[Color]] = {}
    for source in _COLOR_SOURCES:
        parsed = parse_colors(data.get(source), scale=scale)
        if parsed:
            colors[ARAuraScheme(source.index)] = parsed

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

    scheme = ARAuraScheme.from_value(data.get(ARNvramType.AURA_SCHEME))
    scheme_prev = ARAuraScheme.from_value(
        data.get(ARNvramType.AURA_SCHEME_PREV)
    )

    state = raw_to_bool(data.get(ARNvramType.AURA)) or False
    if scheme is ARAuraScheme.OFF:
        state = False

    day_colors = _parse_scheme_colors(data, COLOR_SCALE_ASUS_DAY)

    zones = raw_to_int(data.get(ARNvramType.AURA_COUNT))
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
            raw_to_bool(data.get(ARNvramType.AURA_NIGHT_MODE)) or False
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
