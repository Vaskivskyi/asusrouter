"""Aura action for AsusRouter."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING, Any

from asusrouter.modules.action import ARAction
from asusrouter.modules.aura.effect import (
    apply_brightness,
    apply_color,
    default_colors,
    fit_zones,
)
from asusrouter.modules.aura.enums import (
    AURA_COLOR_SCHEMES,
    ARAuraField,
    ARAuraScheme,
)
from asusrouter.modules.aura.source import ARAuraSourceUniversal
from asusrouter.modules.aura.support import aura_supported
from asusrouter.modules.endpoint import AREndpoint, get_endpoint_request_type
from asusrouter.modules.nvram import ARNvramType
from asusrouter.modules.service.action import ARServiceResult
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.color import COLOR_SCALE_ASUS_DAY, Color, dump_colors
from asusrouter.tools.types import ARCallbackType
from asusrouter.tools.writers import dict_to_request

if TYPE_CHECKING:
    from asusrouter.modules.device.identity import ARDeviceIdentity

_LOGGER = logging.getLogger(__name__)


@dataclass(eq=False, repr=False, kw_only=True)
class ARAuraAction(ARAction):
    """Change the Aura light effect, colors or night mode."""

    scheme: ARAuraScheme | None = None
    color: Color | list[Color] | None = None
    brightness: int | None = None
    zone: int | None = None
    night_mode: bool | None = None


def _resolve_scheme(
    action: ARAuraAction, current: dict[ARAuraField, Any]
) -> ARAuraScheme:
    """Resolve the scheme to apply from the action and current state."""

    if action.scheme is None:
        raw = current.get(ARAuraField.SCHEME, ARAuraScheme.STATIC)
    elif action.scheme is ARAuraScheme.ON:
        raw = current.get(ARAuraField.SCHEME_PREV, ARAuraScheme.STATIC)
    else:
        raw = action.scheme
    scheme = ARAuraScheme.from_value(raw)

    if action.scheme is ARAuraScheme.OFF:
        return ARAuraScheme.OFF
    if scheme in (ARAuraScheme.UNKNOWN, ARAuraScheme.OFF, ARAuraScheme.ON):
        return ARAuraScheme.STATIC
    return scheme


def _build_color_payload(
    action: ARAuraAction,
    current: dict[ARAuraField, Any],
    scheme: ARAuraScheme,
) -> dict[str, str]:
    """Build the ledg_rgb payload for a color scheme."""

    zones = current.get(ARAuraField.ZONES) or 0
    if zones < 1:
        # No zones to color; avoid sending an empty ledg_rgb that wipes colors
        return {}

    stored = current.get(ARAuraField.COLORS, {}).get(scheme)
    colors = fit_zones(list(stored or default_colors(zones)), zones)
    colors = apply_color(colors, action.color, action.zone)
    colors = apply_brightness(colors, action.brightness, action.zone)

    return {
        ARNvramType.AURA_RGB.value: dump_colors(
            colors, scale=COLOR_SCALE_ASUS_DAY
        )
    }


async def run_action(
    callback: ARCallbackType,
    action: ARAuraAction,
    *,
    fetch_data_callback: ARCallbackType | None = None,
    fetch_raw_callback: ARCallbackType | None = None,
    identity: ARDeviceIdentity | None = None,
    **kwargs: Any,
) -> ARServiceResult:
    """Apply the Aura action."""

    if not aura_supported(identity):
        _LOGGER.debug("Aura unsupported on this device; ignoring action")
        return ARServiceResult(success=False)

    current: dict[ARAuraField, Any] = {}
    if fetch_data_callback is not None:
        fetched = await fetch_data_callback(ARAuraSourceUniversal)
        if isinstance(fetched, dict):
            current = fetched.get(ARAuraSourceUniversal) or {}

    scheme = _resolve_scheme(action, current)
    payload: dict[str, Any] = {ARNvramType.AURA_SCHEME.value: int(scheme)}

    # If night mode is supported
    if action.night_mode is not None:
        if ARAuraField.NIGHT_MODE in current:
            payload[ARNvramType.AURA_NIGHT_MODE.value] = action.night_mode
        else:
            _LOGGER.debug("Night mode unsupported; ignoring night_mode change")

    editing_colors = action.color is not None or action.brightness is not None
    if scheme in AURA_COLOR_SCHEMES and editing_colors:
        payload.update(_build_color_payload(action, current, scheme))

    request = dict_to_request(
        payload, request_type=get_endpoint_request_type(AREndpoint.SET_AURA)
    )

    # Post raw: async_fetch returns None on failure and the (ignored) body on
    # success, while async_read would collapse a failed fetch to {} and hide it
    poster = fetch_raw_callback or callback
    data = await poster(endpoint=AREndpoint.SET_AURA, request=request)
    return ARServiceResult(success=data is not None)


ARCallReg.register_action(ARAuraAction, run_action=run_action)


__all__ = [
    "ARAuraAction",
    "run_action",
]
