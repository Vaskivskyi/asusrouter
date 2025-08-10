"""Tests for the color module."""

from unittest.mock import patch

from asusrouter.modules.color import (
    DEFAULT_COLOR,
    DEFAULT_COLOR_SCALE_ASUS,
    ColorRGB,
    ColorRGBB,
    average_color,
    color_zone,
    parse_colors,
)
import pytest


@pytest.mark.parametrize(
    ("colors", "expected"),
    [
        # Single color
        (ColorRGB(255, 0, 0), ColorRGB(255, 0, 0)),
        # Color list
        (
            [
                ColorRGB(128, 0, 0),
                ColorRGB(0, 128, 0),
                ColorRGB(0, 0, 128),
            ],
            ColorRGB(42, 42, 42),
        ),
        # Empty list
        ([], ColorRGB(0, 0, 0, 128)),
        # Color with different scales
        (
            [
                ColorRGB(255, 0, 0, 255),
                ColorRGB(0, 255, 0, 128),
                ColorRGB(0, 0, 255, 64),
            ],
            ColorRGB(85, 42, 21, 255),
        ),
    ],
)
def test_average_color(colors: list[ColorRGB], expected: ColorRGB) -> None:
    """Test average_color."""

    assert average_color(colors) == expected


@pytest.mark.parametrize(
    ("color_str", "delimiter", "expected"),
    [
        # Correct number of color channels
        ("255,0,0", None, 1),
        ("255,0,0,0,255,0", None, 2),
        ("255,0,0,0,255,0,0,0,255", None, 3),
        # Wrong number of color channels
        ("255,0", None, 0),
        ("255,0,0,0,255", None, 1),
        # Empty string or no string
        ("", None, 0),
        (None, None, 0),
        # Different delimiter
        ("255|0|0|0|255|0", "|", 2),
        ("255|0|0|0|255|0|0|0", "|", 2),
    ],
)
def test_color_zone(
    color_str: str | None, delimiter: str | None, expected: int
) -> None:
    """Test color_zone."""

    if delimiter:
        assert color_zone(color_str, delimiter) == expected
    else:
        assert color_zone(color_str) == expected


@pytest.mark.parametrize(
    ("color_str", "delimiter", "scale", "expected"),
    [
        # Correct number of color channels
        ("255,0,0", None, 255, [ColorRGBB((255, 0, 0), 255, 255)]),
        (
            "255,0,0,0,255,0",
            None,
            255,
            [
                ColorRGBB((255, 0, 0), 255, 255),
                ColorRGBB((0, 255, 0), 255, 255),
            ],
        ),
        (
            "255,0,0,0,255,0,0,0,255",
            None,
            255,
            [
                ColorRGBB((255, 0, 0), 255, 255),
                ColorRGBB((0, 255, 0), 255, 255),
                ColorRGBB((0, 0, 255), 255, 255),
            ],
        ),
        # Wrong number of color channels
        ("255,0", None, 255, None),
        ("255,0,0,0,255", None, 255, [ColorRGBB((255, 0, 0), 255, 255)]),
        # Empty string or no string
        ("", None, 255, None),
        (None, None, 255, None),
        # Different delimiter
        (
            "255|0|0|0|255|0",
            "|",
            255,
            [
                ColorRGBB((255, 0, 0), 255, 255),
                ColorRGBB((0, 255, 0), 255, 255),
            ],
        ),
        (
            "255|0|0|0|255|0|0|0",
            "|",
            255,
            [
                ColorRGBB((255, 0, 0), 255, 255),
                ColorRGBB((0, 255, 0), 255, 255),
            ],
        ),
    ],
)
def test_parse_colors(
    color_str: str | None,
    delimiter: str | None,
    scale: int | None,
    expected: list[ColorRGBB] | None,
) -> None:
    """Test parse_colors."""

    if delimiter:
        assert parse_colors(color_str, delimiter, scale) == expected
    else:
        assert parse_colors(color_str, scale=scale) == expected


class TestColorRGB:
    """Test the ColorRGB class."""

    @pytest.mark.parametrize(
        ("r", "g", "b", "scale", "expected"),
        [
            # No values provided
            (None, None, None, None, DEFAULT_COLOR),
            # R provides the whole RGB tuple
            ((255, 0, 0), None, None, 255, (255, 0, 0)),
            # R provides the whole RGB tuple with scale
            ((255, 0, 0), None, None, 128, (128, 0, 0)),
            # No scale provided
            (
                (64431, 0, 0),
                None,
                None,
                None,
                (DEFAULT_COLOR_SCALE_ASUS, 0, 0),
            ),
            # R only provides the R value
            (255, None, None, 255, (255, 255, 255)),
            # All channels are provided
            (100, 150, 200, 255, (100, 150, 200)),
        ],
    )
    def test_initialization(
        self,
        r: int | tuple[int, ...] | None,
        g: int | None,
        b: int | None,
        scale: int | None,
        expected: tuple[int, int, int],
    ) -> None:
        """Test initialization."""

        if scale is not None:
            color = ColorRGB(r, g, b, scale)
        else:
            color = ColorRGB(r, g, b)

        assert (color._r, color._g, color._b) == expected

    @pytest.mark.parametrize(
        ("input_rgb", "expected"),
        [
            # Correct input
            ((100, 150, 200), (100, 150, 200)),
            ("100,150,200", (100, 150, 200)),
            ((100,), (100, 0, 0)),
            ("100", (100, 0, 0)),
            (ColorRGB(32, 48, 64), (32, 48, 64)),
            # Wrong input
            (None, (0, 0, 0)),
        ],
    )
    def test_normalize_input_rgb(
        self,
        input_rgb: str | tuple[int, ...] | ColorRGB | None,
        expected: tuple[int, int, int],
    ) -> None:
        """Test the _normalize_input_rgb method."""

        color = ColorRGB()
        result = color._normalize_input_rgb(input_rgb)
        assert result == expected

    @pytest.mark.parametrize(
        ("values", "scale", "expected"),
        [
            # Normal number of values
            ((100, 200, 300), 255, (85, 170, 255)),
            ((50, 100, 150), 100, (33, 67, 100)),
            ((255, 255, 255), 255, (255, 255, 255)),
            ((0, 0, 0), 255, (0, 0, 0)),
            ((128, 64, 32), 128, (128, 64, 32)),
            # Different number of values
            ((100, 200), 255, (100, 200)),
            ((100, 200, 300, 400), 200, (50, 100, 150, 200)),
        ],
    )
    def test_normalize_scale(
        self,
        values: tuple[int, int, int],
        scale: int,
        expected: tuple[int, int, int],
    ) -> None:
        """Test _normalize_scale."""

        color = ColorRGB()
        result = color._normalize_scale(values, scale)
        assert result == expected

    @pytest.mark.parametrize(
        ("input_rgb", "expected"),
        [
            # This will scale to the default 128 scale
            ((100, 150, 200), (64, 96, 128)),
            ("100,150,200", (64, 96, 128)),
            # This will stay
            ((32, 64, 96), (32, 64, 96)),
            # Other input
            ((100,), (100, 0, 0)),
            ("100", (100, 0, 0)),
            (None, (0, 0, 0)),
        ],
    )
    def test_from_rgb(
        self,
        input_rgb: str | tuple[int, ...] | None,
        expected: tuple[int, int, int],
    ) -> None:
        """Test from_rgb."""

        color = ColorRGB()
        color.from_rgb(input_rgb)
        assert (color._r, color._g, color._b) == expected

    @pytest.mark.parametrize(
        ("rgb", "scale", "expected"),
        [
            # This will scale to the default 128 scale
            ((100, 150, 200), 128, (64, 96, 128)),
            ("100,150,200", 128, (64, 96, 128)),
            # This will scale to the 255 scale
            ((32, 64, 96), 255, (32, 64, 96)),
            # Other input
            ((100,), 255, (100, 0, 0)),
            ("100", 255, (100, 0, 0)),
            (None, 255, (0, 0, 0)),
        ],
    )
    def test_from_rgbs(
        self,
        rgb: str | tuple[int, ...] | None,
        scale: int | None,
        expected: tuple[int, int, int] | None,
    ) -> None:
        """Test from_rgbs."""

        with patch.object(ColorRGB, "from_rgb") as mock_from_rgb:
            color = ColorRGB()
            color.from_rgbs(rgb, scale=scale)

            assert mock_from_rgb.call_count == 2  # noqa: PLR2004

            assert color._scale == scale

    @pytest.mark.parametrize(
        ("input_rgb", "expected"),
        [
            # Correct input
            ((100, 150, 200), (64, 96, 128)),
            ((100,), (100, 0, 0)),
            # Wrong input
            (None, (0, 0, 0)),
        ],
    )
    def test_as_tuple(
        self, input_rgb: tuple[int, ...] | None, expected: tuple[int, int, int]
    ) -> None:
        """Test as_tuple."""

        color = ColorRGB(input_rgb)
        assert color.as_tuple() == expected

    @pytest.mark.parametrize(
        ("input_rgb", "expected"),
        [
            # Correct input
            ((100, 150, 200), "64,96,128"),
            ((100,), "100,0,0"),
            # Wrong input
            (None, "0,0,0"),
        ],
    )
    def test_repr(
        self, input_rgb: tuple[int, ...] | None, expected: str
    ) -> None:
        """Test __repr__."""

        color = ColorRGB(input_rgb)
        assert repr(color) == expected

    @pytest.mark.parametrize(
        ("input_rgb", "expected"),
        [
            # Correct input
            ((100, 150, 200), "64,96,128"),
            ((100,), "100,0,0"),
            # Wrong input
            (None, "0,0,0"),
        ],
    )
    def test_str(
        self, input_rgb: tuple[int, ...] | None, expected: str
    ) -> None:
        """Test __str__."""

        color = ColorRGB(input_rgb)
        assert str(color) == expected

    @pytest.mark.parametrize(
        ("color1", "color2", "expected"),
        [
            # Equal colors
            (ColorRGB(100, 150, 200, 128), ColorRGB(100, 150, 200, 128), True),
            # Different colors
            (
                ColorRGB(100, 150, 200, 255),
                ColorRGB(100, 150, 201, 255),
                False,
            ),
            # Different types
            (ColorRGB(32, 64, 96), "test", False),
        ],
    )
    def test_eq(
        self, color1: ColorRGB, color2: ColorRGB | str, expected: bool
    ) -> None:
        """Test __eq__."""

        assert (color1 == color2) == expected
        assert (color2 == color1) == expected

    @pytest.mark.parametrize(
        ("input_rgb", "expected"),
        [
            # Correct input
            ((100, 150, 200), (64, 96, 128, 128)),
            ((100,), (100, 0, 0, 128)),
            # Wrong input
            (None, (0, 0, 0, 128)),
        ],
    )
    def test_hash(
        self,
        input_rgb: tuple[int, ...] | None,
        expected: tuple[int, int, int, int],
    ) -> None:
        """Test __hash__."""

        color = ColorRGB(input_rgb)
        expected = hash(expected)

        assert hash(color) == expected

    @pytest.mark.parametrize(
        ("input_rgb", "r", "g", "b", "scale", "color_brightness"),
        [
            # Correct input
            ((100, 150, 200), 64, 96, 128, 128, 128),
            ((100,), 100, 0, 0, 128, 100),
            # Wrong input
            (None, 0, 0, 0, 128, 0),
        ],
    )
    def test_properties(  # noqa: PLR0913
        self,
        input_rgb: tuple[int, ...] | None,
        r: int,
        g: int,
        b: int,
        scale: int,
        color_brightness: int,
    ) -> None:
        """Test properties."""

        color = ColorRGB(input_rgb)
        assert color.r == r
        assert color.g == g
        assert color.b == b
        assert color.scale == scale
        assert color.color_brightness == color_brightness


class TestColorRGBB:
    """Test the ColorRGBB class."""

    @pytest.mark.parametrize(
        ("rgb", "br", "scale", "expected"),
        [
            # Empty
            (None, None, None, (0, 0, 0, 128, 128)),
            # RGB colors
            ((100, 150, 200), None, None, (64, 96, 128, 128, 128)),
            (ColorRGB(100, 150, 200), None, None, (64, 96, 128, 128, 128)),
            ((100, 150, 200), 64, None, (64, 96, 128, 64, 128)),
            ((100, 150, 200), None, 64, (32, 48, 64, 64, 64)),
        ],
    )
    def test_initialization(
        self,
        rgb: tuple[int, ...] | None,
        br: int | None,
        scale: int | None,
        expected: tuple[int, int, int, int, int],
    ) -> None:
        """Test initialization."""

        # Remap None to defaults
        br = br or DEFAULT_COLOR_SCALE_ASUS
        scale = scale or DEFAULT_COLOR_SCALE_ASUS

        color = ColorRGBB(rgb, br, scale)
        assert (
            color._r,
            color._g,
            color._b,
            color._br,
            color._scale,
        ) == expected

    @pytest.mark.parametrize(
        ("br", "expected"),
        [
            # Correct values
            (64, 64),
            (128, 128),
            (255, 128),
            # Wrong values
            (-1, 0),
            # Out of scale
            (256, 128),
        ],
    )
    def test_set_brightness(self, br: int | None, expected: int) -> None:
        """Test set_brightness."""

        color = ColorRGBB()
        color.set_brightness(br)
        assert color._br == expected

    @pytest.mark.parametrize(
        ("rgb", "scale", "expected"),
        [
            # Correct input
            ((100, 150, 200), 128, (64, 96, 128)),
            ("100,150,200", 128, (64, 96, 128)),
            ((100, 150, 200), None, (64, 96, 128)),
            # Wrong input
            (None, 128, (0, 0, 0)),
        ],
    )
    def test__from_rgb(
        self,
        rgb: str | tuple[int, ...] | None,
        scale: int | None,
        expected: tuple[int, int, int],
    ) -> None:
        """Test _from_rgb."""

        color = ColorRGBB()
        result = color._from_rgb(rgb, scale=scale)
        assert result == expected

    @pytest.mark.parametrize(
        ("rgb", "scale", "expected"),
        [
            # Correct input
            ((100, 150, 200), 128, (64, 96, 128)),
            ("100,150,200", 128, (64, 96, 128)),
            (ColorRGB(100, 150, 200), None, (64, 96, 128)),
            ((100, 150, 200), None, (64, 96, 128)),
            # Wrong input
            (None, 128, (0, 0, 0)),
        ],
    )
    def test_from_rgb(
        self,
        rgb: str | tuple[int, ...] | ColorRGB | None,
        scale: int | None,
        expected: tuple[int, int, int],
    ) -> None:
        """Test from_rgb."""

        color = ColorRGBB()
        color.from_rgb(rgb, scale=scale)
        assert (color._r, color._g, color._b) == expected

    @pytest.mark.parametrize(
        ("rgb", "scale", "expected"),
        [
            # Correct input
            ((100, 150, 200), 128, (64, 96, 128)),
            (ColorRGB(100, 150, 200), None, (64, 96, 128)),
            ((32, 64, 96), None, (43, 85, 128)),
            # Wrong input
            (None, 128, (0, 0, 0)),
        ],
    )
    def test_from_rgbwb(
        self,
        rgb: str | tuple[int, ...] | ColorRGB | None,
        scale: int | None,
        expected: tuple[int, int, int],
    ) -> None:
        """Test from_rgbwb."""

        color = ColorRGBB()
        color.from_rgbwb(rgb, scale=scale)
        assert (color._r, color._g, color._b) == expected

    @pytest.mark.parametrize(
        ("rgb", "scale", "rgbb", "expected"),
        [
            # Self test
            ((32, 48, 64), 128, None, (64, 96, 128)),
            ((64, 96, 128), 128, None, (64, 96, 128)),
            # No scale
            ((32, 48, 64), 128, (100, 150, 200, 128), (100, 150, 200)),
            # Scale up
            ((32, 48, 64), 128, (100, 150, 200, 255), (199, 255, 255)),
            # Scale down
            ((32, 48, 64), 128, (100, 150, 200, 64), (50, 64, 64)),
        ],
    )
    def test__to_rgb(
        self,
        rgb: tuple[int, ...] | None,
        scale: int | None,
        rgbb: tuple[int, ...] | None,
        expected: tuple[int, int, int],
    ) -> None:
        """Test _to_rgb."""

        color = ColorRGBB(rgb, scale=scale)
        result = color._to_rgb(rgbb)
        assert result == expected

    @pytest.mark.parametrize(
        ("input_color", "scale", "expected_rgb"),
        [
            (
                ColorRGBB((255, 0, 0), scale=255),
                None,
                ColorRGB(255, 0, 0, 255),
            ),
            (ColorRGBB((0, 255, 0), scale=255), 128, ColorRGB(0, 128, 0, 255)),
            (ColorRGBB((0, 0, 255), scale=255), 64, ColorRGB(0, 0, 64, 255)),
        ],
    )
    def test_to_rgb(
        self, input_color: ColorRGBB, scale: int | None, expected_rgb: ColorRGB
    ) -> None:
        """Test to_rgb."""

        result = input_color.to_rgb(scale)
        assert result.as_tuple() == expected_rgb.as_tuple()

    @pytest.mark.parametrize(
        ("input_color", "expected"),
        [
            (ColorRGBB((255, 0, 0), 128, 255), "255,0,0,128,255"),
            (ColorRGBB((0, 255, 0), 64, 255), "0,255,0,64,255"),
            (ColorRGBB((0, 0, 255), 32, 255), "0,0,255,32,255"),
        ],
    )
    def test_repr(self, input_color: ColorRGBB, expected: str) -> None:
        """Test __repr__."""

        assert repr(input_color) == expected

    @pytest.mark.parametrize(
        ("input_color", "expected"),
        [
            (ColorRGBB((255, 0, 0), 128, 255), "255,0,0,128,255"),
            (ColorRGBB((0, 255, 0), 64, 255), "0,255,0,64,255"),
            (ColorRGBB((0, 0, 255), 32, 255), "0,0,255,32,255"),
        ],
    )
    def test_str(self, input_color: ColorRGBB, expected: str) -> None:
        """Test __str__."""

        assert str(input_color) == expected

    @pytest.mark.parametrize(
        ("input_color", "r", "g", "b", "br", "scale"),
        [
            (ColorRGBB((100, 150, 200), 128, 128), 64, 96, 128, 128, 128),
            (ColorRGBB((100, 150, 200), 64, 128), 64, 96, 128, 64, 128),
            (ColorRGBB((100, 150, 200), 128, 64), 32, 48, 64, 64, 64),
        ],
    )
    def test_properties(  # noqa: PLR0913
        self,
        input_color: ColorRGBB,
        r: int,
        g: int,
        b: int,
        br: int,
        scale: int,
    ) -> None:
        """Test properties."""

        assert input_color.r == r
        assert input_color.g == g
        assert input_color.b == b
        assert input_color.brightness == br
        assert input_color.scale == scale
