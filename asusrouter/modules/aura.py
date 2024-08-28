"""Aura module."""

from __future__ import annotations

import logging
import re
from enum import Enum, IntEnum
from typing import Any, Awaitable, Callable, Optional

from asusrouter.modules.color import (
    ColorRGB,
    ColorRGBB,
    average_color,
    parse_colors,
)
from asusrouter.modules.data import AsusData, AsusDataState
from asusrouter.modules.endpoint import EndpointTools
from asusrouter.modules.identity import AsusDevice
from asusrouter.tools.converters import (
    get_arguments,
    safe_bool,
    safe_enum,
    safe_int,
)

_LOGGER = logging.getLogger(__name__)


class AsusAura(IntEnum):
    """Asus Aura state."""

    UNKNOWN = -999
    ON = -1
    OFF = 0
    GRADIENT = 1
    STATIC = 2
    BREATHING = 3
    EVOLUTION = 4
    RAINBOW = 5
    WAVE = 6
    MARQUEE = 7


class AsusAuraColor(IntEnum):
    """Asus Aura with color support."""

    GRADIENT = 1
    STATIC = 2
    BREATHING = 3
    MARQUEE = 7


class DefaultAuraColor(Enum):
    """Default Aura colors."""

    COLOR1 = ColorRGBB((20, 0, 128))
    COLOR2 = ColorRGBB((110, 0, 100))
    COLOR3 = ColorRGBB((128, 0, 80))


DEFAULT_COLOR_PATTERN = (
    DefaultAuraColor.COLOR1,
    DefaultAuraColor.COLOR2,
    DefaultAuraColor.COLOR3,
    DefaultAuraColor.COLOR2,
)

DEFAULT_AURA_SCHEME = AsusAura.STATIC


def get_default_aura_color(zones: int) -> tuple[ColorRGBB, ...]:
    """Get the default Aura color for the zones."""

    _pattern_length = len(DEFAULT_COLOR_PATTERN)
    # Repeat the pattern enough times to cover the required length
    repeated_pattern = DEFAULT_COLOR_PATTERN * (
        (zones + _pattern_length - 1) // _pattern_length
    )

    # Return the required length
    return tuple(color.value for color in repeated_pattern[:zones])


def get_scheme_from_state(aura_state: dict) -> AsusAura:
    """Get the scheme from the state."""

    def is_valid_scheme(scheme: Any) -> bool:
        """Check if the scheme is valid."""

        # Keep compatible with Python 3.11,
        valid_schemes = [
            e.value
            for e in AsusAura
            if e not in (AsusAura.UNKNOWN, AsusAura.ON, AsusAura.OFF)
        ]
        return scheme in valid_schemes

    current_scheme = safe_int(aura_state.get("scheme"))
    if current_scheme is not None and is_valid_scheme(current_scheme):
        return AsusAura(current_scheme)

    prev_scheme = safe_int(aura_state.get("scheme_prev"))
    if prev_scheme is not None and is_valid_scheme(prev_scheme):
        return AsusAura(prev_scheme)

    return DEFAULT_AURA_SCHEME


def set_color(
    colors: list[ColorRGBB],
    color_to_set: Optional[ColorRGB | list[ColorRGB]],
    zone: Optional[int] = None,
    zones: Optional[int] = None,
) -> None:
    """Set new color(s) to the existing color list."""

    # Fallback in case zones have wrong data written
    zones = zones or len(colors)

    # Make sure, we have enough colors in the list (fix wrong data)
    if len(colors) < zones:
        colors.extend(colors[: zones - len(colors)])

    # No new color defined
    if not color_to_set:
        _LOGGER.debug("No new color defined. Skipping")
        return

    if isinstance(color_to_set, ColorRGB):
        _LOGGER.debug("Single color defined: %s", color_to_set)
        # Single zone defined
        if zone is not None and zone < zones:
            _LOGGER.debug("Applying the color to the zone %s", zone)
            colors[zone].from_rgb(color_to_set)
        # No zone defined - set the color to all zones
        else:
            _LOGGER.debug("Applying the color to all zones")
            for i in range(zones):
                colors[i].from_rgb(color_to_set)
        return

    if isinstance(color_to_set, list):
        # We have a list of colors to set
        _LOGGER.debug("List of colors defined")
        for i in range(zones):
            color = color_to_set[i % len(color_to_set)]
            if isinstance(color, ColorRGB):
                colors[i].from_rgb(color)

    return


def set_brightness(
    colors: list[ColorRGBB],
    brightness: Optional[int],
    zone: Optional[int] = None,
) -> None:
    """Set the brightness for the zones."""

    # Prepare the brightness
    brightness = safe_int(brightness)

    # No brightness defined
    if brightness is None:
        return

    # Change the brightness for the selected zone
    if isinstance(zone, int) and 0 <= zone < len(colors):
        colors[zone].set_brightness(brightness)
        return

    # Change the brightness for all zones
    for color in colors:
        color.set_brightness(brightness)

    return


async def set_state(
    callback: Callable[..., Awaitable[bool]],
    state: AsusAura,
    **kwargs: Any,
) -> bool:
    """Set the Aura state."""

    # Get the identity
    identity: AsusDevice = kwargs.get("identity", AsusDevice())
    # Get the number of zones
    zones = identity.aura_zone
    if zones < 1:
        _LOGGER.debug("No Aura zones found. Skipping the Aura service.")
        return False

    # Get the current router state
    aura_state = (
        kwargs.get("router_state", {}).get(AsusData.AURA, AsusDataState).data
    )

    # Get the arguments
    color_to_set, brightness, zone = get_arguments(
        ("color", "brightness", "zone"), **kwargs
    )

    if state == AsusAura.ON:
        _LOGGER.debug("Aura effect not specified. Checking the previous state")
        # Get the previous state
        state = get_scheme_from_state(aura_state)

    # Check if the state has color support
    if state.name not in AsusAuraColor.__members__:
        # No color selection for the state
        _LOGGER.debug(
            "Setting the Aura state to `%s`. No color / brightness support for this state",
            state.name,
        )
        return await callback(
            endpoint=EndpointTools.AURA,
            commands={"ledg_scheme": state.value},
        )

    # Get the state number
    state_number = AsusAuraColor[state.name].value

    # Get the previous colors / fallback to the default color
    colors = aura_state.get("effect", {}).get(
        state_number, get_default_aura_color(zones)
    )
    # Convert to ColorRGBB if needed
    colors = [
        ColorRGBB(color) if isinstance(color, ColorRGB) else color
        for color in colors
    ]

    # Set new color(s) and brightness
    set_color(colors, color_to_set, zone, zones)
    set_brightness(colors, brightness, zone)

    # Convert color_set to the string
    color_to_use = ",".join(
        [color_zone.to_rgb().__str__() for color_zone in colors]
    )
    _LOGGER.debug("Setting the Aura color to `%s`", color_to_use)

    # Prepare the arguments
    arguments = {
        "ledg_scheme": state.value,
        "ledg_rgb": color_to_use,
    }

    # Run the service
    return await callback(
        endpoint=EndpointTools.AURA,
        commands=arguments,
    )


def process_aura(data: dict[str, Any]) -> dict[str, Any]:
    """Process Aura data."""

    def get_scheme(key: str) -> AsusAura:
        """Get the scheme from the data."""

        scheme_value = data.get(key)
        _scheme_value = safe_int(scheme_value)
        _scheme_enum = safe_enum(AsusAura, _scheme_value, default_value=-999)
        scheme: AsusAura = (
            _scheme_enum if _scheme_enum is not None else AsusAura.UNKNOWN
        )

        if scheme == AsusAura.UNKNOWN and _scheme_value is not None:
            _LOGGER.warning("Unknown Aura scheme: `%s`", scheme_value)
        return scheme

    # Get the effects data
    rgb_key_pattern = re.compile(r"ledg_rgb(\d+)")
    effect = {
        safe_int(match.group(1)): parse_colors(data[key])
        for key in data
        if (match := rgb_key_pattern.match(key))
    }

    aura = {
        "state": safe_bool(data.get("AllLED")),
        "night_mode": safe_bool(data.get("ledg_night_mode")),
        "scheme": get_scheme("ledg_scheme"),
        "scheme_prev": get_scheme("ledg_scheme_old"),
        "effect": effect,
        "active": {},
    }

    if aura["scheme"] == AsusAura.OFF:
        aura["state"] = False

    # Active effect
    active_effect = aura["effect"].get(aura["scheme"].value)
    if active_effect:
        _active_brightness = 0
        for i, color in enumerate(active_effect):
            _brightness = color.brightness
            aura["active"][i] = {"color": color, "brightness": _brightness}
            _active_brightness = max(_active_brightness, _brightness)

        # Active color and brightness
        active_color = ColorRGBB(average_color(active_effect))
        active_color.set_brightness(_active_brightness)
        aura["active"]["color"] = active_color
        aura["active"]["brightness"] = _active_brightness

    print(aura["effect"])

    # Get number of zones from the Static effect length
    _effect_static = aura["effect"].get(AsusAuraColor.STATIC)
    aura["zones"] = len(_effect_static) if _effect_static else 0

    return aura
