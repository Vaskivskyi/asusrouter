"""Aura enums for AsusRouter."""

from __future__ import annotations

from enum import IntEnum, StrEnum

from asusrouter.const import UNKNOWN_MEMBER, UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromIntMixin, FromStrMixin


class ARAuraScheme(FromIntMixin, IntEnum):
    """Aura light effect scheme. Values are the device `ledg_scheme` codes."""

    UNKNOWN = UNKNOWN_MEMBER

    ON = -1  # restore the previous scheme
    OFF = 0
    GRADIENT = 1
    STATIC = 2
    BREATHING = 3
    EVOLUTION = 4
    RAINBOW = 5
    WAVE = 6
    MARQUEE = 7


# Schemes whose colors are user-defined and sent on change
AURA_COLOR_SCHEMES = frozenset(
    {
        ARAuraScheme.GRADIENT,
        ARAuraScheme.STATIC,
        ARAuraScheme.BREATHING,
        ARAuraScheme.MARQUEE,
    }
)


class ARAuraField(FromStrMixin, StrEnum):
    """Keys of the Aura data dict."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    BRIGHTNESS = "brightness"  # active scheme peak brightness
    COLOR = "color"  # active scheme blended color
    COLORS = "colors"  # colors per scheme
    NIGHT_COLORS = "night_colors"  # reserved; not in use
    NIGHT_MODE = "night_mode"
    SCHEME = "scheme"
    SCHEME_PREV = "scheme_prev"
    SDN = "sdn"  # reserved; not in use
    STATE = "state"  # master LED on/off
    ZONES = "zones"


__all__ = [
    "AURA_COLOR_SCHEMES",
    "ARAuraField",
    "ARAuraScheme",
]
