"""Color tools."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Final

from asusrouter.tools.converters_v2.raw import raw_to_int, raw_to_str

# Canonical full-brightness scale for a stored color
COLOR_SCALE: Final[int] = 255

# ASUS Aura stores day colors halved
COLOR_SCALE_ASUS_DAY: Final[int] = 128

COLOR_DELIMITER: Final[str] = ","

_CHANNELS: Final[int] = 3


def _clamp(value: int, high: int, low: int = 0) -> int:
    """Clamp the value into the inclusive range."""

    return max(low, min(value, high))


def _rescale(value: int, scale_to: int, scale_from: int) -> int:
    """Rescale the value between two scales, clamped to the target."""

    if scale_from <= 0:
        return 0
    return _clamp(round(value * scale_to / scale_from), scale_to)


@dataclass(frozen=True, slots=True)
class Color:
    """An RGB color with hue held at full brightness and brightness separate.

    `red`/`green`/`blue` hold the hue at full brightness on `0..COLOR_SCALE`
    and `brightness` scales it on output. This mirrors how ASUS Aura encodes a
    color, where the largest channel carries the brightness and the channel
    ratios carry the hue.
    """

    red: int = 0
    green: int = 0
    blue: int = 0
    brightness: int = COLOR_SCALE

    def __post_init__(self) -> None:
        """Clamp all components into the valid range."""

        object.__setattr__(self, "red", _clamp(self.red, COLOR_SCALE))
        object.__setattr__(self, "green", _clamp(self.green, COLOR_SCALE))
        object.__setattr__(self, "blue", _clamp(self.blue, COLOR_SCALE))
        object.__setattr__(
            self, "brightness", _clamp(self.brightness, COLOR_SCALE)
        )

    @classmethod
    def from_asus(cls, r: int, g: int, b: int, *, scale: int) -> Color:
        """Build a color from ASUS channels with brightness embedded."""

        channels = (_clamp(r, scale), _clamp(g, scale), _clamp(b, scale))
        brightness_raw = max(channels)
        if brightness_raw == 0:
            return cls(0, 0, 0, 0)

        # Hue: normalize each channel to full brightness on the canonical scale
        hue = tuple(
            _rescale(ch, COLOR_SCALE, brightness_raw) for ch in channels
        )
        brightness = _rescale(brightness_raw, COLOR_SCALE, scale)

        return cls(hue[0], hue[1], hue[2], brightness)

    def to_asus(self, *, scale: int) -> tuple[int, int, int]:
        """Return ASUS channels with brightness re-embedded at the scale."""

        # Re-embed brightness on the canonical scale, then rescale to target
        embedded = tuple(
            _rescale(ch * self.brightness, scale, COLOR_SCALE * COLOR_SCALE)
            for ch in (self.red, self.green, self.blue)
        )

        return embedded[0], embedded[1], embedded[2]

    def with_brightness(self, brightness: int) -> Color:
        """Return a copy with the brightness replaced."""

        return replace(self, brightness=_clamp(brightness, COLOR_SCALE))

    @classmethod
    def blend(cls, colors: list[Color]) -> Color:
        """Blend colors into their average hue at the peak brightness."""

        if not colors:
            return cls()

        count = len(colors)
        red = sum(color.red for color in colors) // count
        green = sum(color.green for color in colors) // count
        blue = sum(color.blue for color in colors) // count
        brightness = max(color.brightness for color in colors)

        return cls(red, green, blue, brightness)


def parse_colors(
    raw: str | None,
    *,
    scale: int,
    delimiter: str = COLOR_DELIMITER,
) -> list[Color]:
    """Parse a delimited ASUS color string into a list of colors."""

    text = raw_to_str(raw)
    if not text:
        return []

    channels = text.split(delimiter)
    return [
        Color.from_asus(
            raw_to_int(channels[i]) or 0,
            raw_to_int(channels[i + 1]) or 0,
            raw_to_int(channels[i + 2]) or 0,
            scale=scale,
        )
        for i in range(0, len(channels) - _CHANNELS + 1, _CHANNELS)
    ]


def dump_colors(
    colors: list[Color],
    *,
    scale: int,
    delimiter: str = COLOR_DELIMITER,
) -> str:
    """Serialize colors back into a delimited ASUS color string."""

    channels: list[int] = []
    for color in colors:
        channels.extend(color.to_asus(scale=scale))

    return delimiter.join(str(channel) for channel in channels)


__all__ = [
    "COLOR_SCALE",
    "COLOR_SCALE_ASUS_DAY",
    "Color",
    "dump_colors",
    "parse_colors",
]
