"""Aura effect color helpers for AsusRouter."""

from __future__ import annotations

from asusrouter.tools.color import COLOR_SCALE_ASUS_DAY, Color

# Default color pattern, repeated across zones when no colors are stored
_DEFAULT_PATTERN = (
    Color.from_asus(20, 0, 128, scale=COLOR_SCALE_ASUS_DAY),
    Color.from_asus(110, 0, 100, scale=COLOR_SCALE_ASUS_DAY),
    Color.from_asus(128, 0, 80, scale=COLOR_SCALE_ASUS_DAY),
    Color.from_asus(110, 0, 100, scale=COLOR_SCALE_ASUS_DAY),
)


def default_colors(zones: int) -> list[Color]:
    """Return the default color for each zone."""

    length = len(_DEFAULT_PATTERN)
    return [_DEFAULT_PATTERN[index % length] for index in range(max(zones, 0))]


def fit_zones(colors: list[Color], zones: int) -> list[Color]:
    """Fit the color list to the zone count, padding from defaults."""

    if zones <= 0:
        return list(colors)

    fitted = list(colors[:zones])
    if len(fitted) < zones:
        fitted.extend(default_colors(zones)[len(fitted) :])

    return fitted


def apply_color(
    colors: list[Color],
    color: Color | list[Color] | None,
    zone: int | None = None,
) -> list[Color]:
    """Apply new color(s) to the zones, preserving each zone's brightness."""

    if color is None:
        return colors

    result = list(colors)

    if isinstance(color, Color):
        # A single color goes to one zone or, without a zone, to all of them
        targets = (
            [zone]
            if zone is not None and 0 <= zone < len(result)
            else range(len(result))
        )
        for index in targets:
            result[index] = color.with_brightness(result[index].brightness)
        return result

    # A list of colors is applied cyclically across the zones
    if color:
        for index in range(len(result)):
            source = color[index % len(color)]
            result[index] = source.with_brightness(result[index].brightness)

    return result


def apply_brightness(
    colors: list[Color],
    brightness: int | None,
    zone: int | None = None,
) -> list[Color]:
    """Apply a brightness to one zone or to all of them."""

    if brightness is None:
        return colors

    result = list(colors)
    if zone is not None and 0 <= zone < len(result):
        result[zone] = result[zone].with_brightness(brightness)
        return result

    return [color.with_brightness(brightness) for color in result]


__all__ = [
    "apply_brightness",
    "apply_color",
    "default_colors",
    "fit_zones",
]
