"""Color module."""

from __future__ import annotations

import logging
from typing import Any, Optional

from asusrouter.tools.converters import clean_input, safe_int, scale_value_int

_LOGGER = logging.getLogger(__name__)

DEFAULT_COLOR = (0, 0, 0)
DEFAULT_COLOR_SCALE = 255
DEFAULT_COLOR_SCALE_ASUS = 128
DEFAULT_COLOR_DELIMITER = ","


def average_color(
    colors: ColorRGB | list[ColorRGB],
) -> ColorRGB:
    """Get the average color."""

    if isinstance(colors, ColorRGB):
        return colors

    if not colors:
        return ColorRGB()

    # Get the scale as the maximum scale from the colors
    scale = max(color.scale for color in colors)

    # Calculate the average color components
    num_colors = len(colors)
    red = sum(color.r for color in colors) // num_colors
    green = sum(color.g for color in colors) // num_colors
    blue = sum(color.b for color in colors) // num_colors

    return ColorRGB(red, green, blue, scale=scale)


@clean_input
def color_zone(
    color_str: Optional[str],
    delimiter: str = ",",
) -> int:
    """Return the number of color zones."""

    if not color_str:
        return 0

    return (len(color_str.split(delimiter))) // 3


@clean_input
def parse_colors(
    color_str: Optional[str],
    delimiter: str = ",",
    scale: int = DEFAULT_COLOR_SCALE_ASUS,
) -> Optional[list[ColorRGBB]]:
    """Parse the colors from the string."""

    if not color_str:
        return None

    # Split the string to separate groups of 3 digits
    channels = color_str.split(delimiter)
    if len(channels) % 3 != 0:
        _LOGGER.warning(
            "Invalid color string: %s, but will parse what is possible",
            color_str,
        )

    colors = []
    for i in range(0, len(channels), 3):
        color = ColorRGBB()
        if i + 2 >= len(channels):
            break
        color.from_rgbwb(
            rgb=(
                safe_int(channels[i]),
                safe_int(channels[i + 1]),
                safe_int(channels[i + 2]),
            ),
            scale=scale,
        )
        colors.append(color)

    return colors if len(colors) > 0 else None


class ColorRGB:
    """RGB color class."""

    def __init__(
        self,
        r: int | tuple[int, int, int] | Any = DEFAULT_COLOR,
        g: Optional[int] = None,
        b: Optional[int] = None,
        scale: int = DEFAULT_COLOR_SCALE_ASUS,
    ) -> None:
        """Initialize the color."""

        self._r: int
        self._g: int
        self._b: int
        self._scale = scale

        # Single value(s)
        if isinstance(r, int):
            g = g if g is not None else r
            b = b if b is not None else r
            self.from_rgb((r, g, b))
            return

        # Any other than tuple
        if not isinstance(r, tuple):
            r = DEFAULT_COLOR

        self.from_rgb(r)
        return

    def _normalize_input_rgb(
        self,
        rgb: Optional[tuple[int, ...] | str],
        delimiter: str = DEFAULT_COLOR_DELIMITER,
    ) -> tuple[int, int, int]:
        """Normalize the RGB input."""

        if rgb is None:
            return DEFAULT_COLOR

        if isinstance(rgb, str):
            rgb = tuple(safe_int(value) for value in rgb.split(delimiter))
        elif isinstance(rgb, ColorRGB):
            rgb = rgb.as_tuple()
        else:
            rgb = tuple(safe_int(value) for value in rgb)

        # Add extra values if needed or remove them
        rgb = (rgb + (0,) * 3)[:3]

        return rgb[0], rgb[1], rgb[2]

    def _normalize_scale(
        self,
        values: tuple[int, ...],
        scale: int,
    ) -> tuple[int, ...]:
        """Normalize the input values to the scale."""

        _brightness = max(values)
        if _brightness > scale:
            values = tuple(
                scale_value_int(value, scale, _brightness) for value in values
            )

        return values

    def from_rgb(
        self,
        rgb: tuple[int, ...] | str,
        delimiter: str = DEFAULT_COLOR_DELIMITER,
    ) -> None:
        """Load a color from RGB values."""

        # Prepare and normalize the input
        rgb = self._normalize_scale(
            self._normalize_input_rgb(rgb, delimiter),
            self._scale,
        )

        # Set the RGB values
        self._r, self._g, self._b = rgb

    def from_rgbs(
        self,
        rgb: tuple[int, int, int] | str,
        delimiter: str = DEFAULT_COLOR_DELIMITER,
        scale: Optional[int] = None,
    ) -> None:
        """Load a color from RGB + Scale values."""

        self._scale = scale or self._scale
        self.from_rgb(rgb, delimiter)

    def as_tuple(self) -> tuple[int, int, int]:
        """Return the color as tuple."""

        return self._r, self._g, self._b

    def __repr__(self) -> str:
        """Return the color as string."""

        return f"{self._r},{self._g},{self._b}"

    def __str__(self) -> str:
        """Return the color as string."""

        return f"{self._r},{self._g},{self._b}"

    def __eq__(self, other: object) -> bool:
        """Check if the colors are equal."""

        if not isinstance(other, ColorRGB):
            return False
        return (
            self._r == other._r
            and self._g == other._g
            and self._b == other._b
            and self._scale == other._scale
        )

    def __hash__(self) -> int:
        """Return the hash of the object."""

        return hash((self._r, self._g, self._b, self._scale))

    @property
    def r(self) -> int:
        return self._r

    @property
    def g(self) -> int:
        return self._g

    @property
    def b(self) -> int:
        return self._b

    @property
    def scale(self) -> int:
        return self._scale

    @property
    def color_brightness(self) -> int:
        return max(self._r, self._g, self._b)


class ColorRGBB(ColorRGB):
    """RGB + Brightness color class."""

    def __init__(
        self,
        rgb: tuple[int, int, int] | ColorRGB = DEFAULT_COLOR,
        br: Optional[int] = None,
        scale: int = DEFAULT_COLOR_SCALE_ASUS,
    ) -> None:
        """Initialize the color."""

        self._scale = scale
        self.from_rgbwb(rgb)
        self._br = min(br, self._scale) if br is not None else self._scale

    def set_brightness(self, br: int) -> None:
        """Set the brightness."""

        self._br = max(0, min(br, self._scale))

    def _from_rgb(
        self,
        rgb: tuple[int, ...] | str,
        delimiter: str = DEFAULT_COLOR_DELIMITER,
        scale: Optional[int] = None,
    ) -> tuple[int, int, int]:
        """Read the RGB values."""

        # Prepare and normalize the input
        rgb = self._normalize_scale(
            self._normalize_input_rgb(rgb, delimiter),
            scale or self._scale,
        )

        return rgb[0], rgb[1], rgb[2]

    def from_rgb(
        self,
        rgb: tuple[int, ...] | str | ColorRGB,
        delimiter: str = DEFAULT_COLOR_DELIMITER,
        scale: Optional[int] = None,
    ) -> None:
        """Load a color from RGB values."""

        if isinstance(rgb, ColorRGB):
            rgb = (rgb.r, rgb.g, rgb.b)

        self._scale = scale or self._scale
        rgb = self._from_rgb(rgb, delimiter, self._scale)

        self._r, self._g, self._b = rgb

    def from_rgbwb(
        self,
        rgb: tuple[int, ...] | ColorRGB,
        delimiter: str = DEFAULT_COLOR_DELIMITER,
        scale: Optional[int] = None,
    ) -> None:
        """Load a color from RGB/wb (RGB with B embedded) values."""

        if isinstance(rgb, ColorRGB):
            rgb = (rgb.r, rgb.g, rgb.b)

        self._scale = scale or self._scale
        rgb = self._from_rgb(rgb, delimiter, self._scale)

        # Get color brightness
        self._br = max(rgb)

        # Rescale RGB to the full scale
        rgb = tuple(
            scale_value_int(value, self._scale, self._br) for value in rgb
        )
        self._r, self._g, self._b = rgb

    def _to_rgb(
        self,
        rgbb: Optional[tuple[int, ...]] = None,
    ) -> tuple[int, int, int]:
        """Return RGBB color as RGB."""

        if rgbb is not None and len(rgbb) >= 4:
            return (
                scale_value_int(rgbb[0], rgbb[3], self._scale),
                scale_value_int(rgbb[1], rgbb[3], self._scale),
                scale_value_int(rgbb[2], rgbb[3], self._scale),
            )

        return (
            scale_value_int(self._r, self._br, self._scale),
            scale_value_int(self._g, self._br, self._scale),
            scale_value_int(self._b, self._br, self._scale),
        )

    def to_rgb(
        self,
        scale: Optional[int] = None,
    ) -> ColorRGB:
        """Return RGBB color as RGB."""

        rgb = self._to_rgb()

        if scale is not None:
            return ColorRGB(self._to_rgb((rgb[0], rgb[1], rgb[2], scale)))

        return ColorRGB(rgb, scale=self._scale)

    def __repr__(self) -> str:
        """Return the color as string."""

        return f"{self._r},{self._g},{self._b},{self._br},{self._scale}"

    def __str__(self) -> str:
        """Return the color as string."""

        return f"{self._r},{self._g},{self._b},{self._br},{self._scale}"

    @property
    def brightness(self) -> int:
        return self._br
