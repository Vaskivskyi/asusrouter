"""Tests for the color tools."""

from __future__ import annotations

import pytest

from asusrouter.tools.color import (
    COLOR_SCALE,
    COLOR_SCALE_ASUS_DAY,
    Color,
    _rescale,
    dump_colors,
    parse_colors,
)


def test_rescale_zero_source() -> None:
    """Rescaling from a non-positive scale yields zero."""

    assert _rescale(100, 255, 0) == 0
    assert _rescale(100, 255, -5) == 0


class TestColor:
    """Tests for the Color value type."""

    def test_defaults(self) -> None:
        """Default color is black at full brightness."""

        color = Color()
        assert (color.red, color.green, color.blue) == (0, 0, 0)
        assert color.brightness == COLOR_SCALE

    @pytest.mark.parametrize(
        ("component", "value", "expected"),
        [
            ("red", 300, COLOR_SCALE),
            ("green", -5, 0),
            ("blue", 128, 128),
            ("brightness", 999, COLOR_SCALE),
        ],
    )
    def test_clamped(self, component: str, value: int, expected: int) -> None:
        """Components are clamped into the valid range."""

        color = Color(**{component: value})
        assert getattr(color, component) == expected

    def test_frozen(self) -> None:
        """Color is immutable."""

        color = Color(1, 2, 3)
        with pytest.raises(AttributeError):
            color.red = 10  # type: ignore[misc]

    def test_from_asus_zero(self) -> None:
        """An all-zero color has zero brightness."""

        color = Color.from_asus(0, 0, 0, scale=COLOR_SCALE_ASUS_DAY)
        assert color == Color(0, 0, 0, 0)

    def test_from_asus_normalizes_hue(self) -> None:
        """Hue is scaled to full brightness, brightness kept separate."""

        color = Color.from_asus(10, 0, 64, scale=COLOR_SCALE_ASUS_DAY)
        assert color.red == round(10 * COLOR_SCALE / 64)
        assert color.green == 0
        assert color.blue == COLOR_SCALE
        assert color.brightness == round(
            64 * COLOR_SCALE / COLOR_SCALE_ASUS_DAY
        )

    def test_from_asus_clamps_channels(self) -> None:
        """Channels above the scale are clamped before parsing."""

        color = Color.from_asus(200, 0, 0, scale=COLOR_SCALE_ASUS_DAY)
        # 200 clamped to 128 -> full brightness red
        assert color.red == COLOR_SCALE
        assert color.brightness == COLOR_SCALE

    @pytest.mark.parametrize("scale", [COLOR_SCALE_ASUS_DAY, COLOR_SCALE])
    @pytest.mark.parametrize(
        ("r", "g", "b"),
        [(10, 0, 64), (128, 64, 32), (0, 0, 0), (100, 100, 100)],
    )
    def test_round_trip(self, scale: int, r: int, g: int, b: int) -> None:
        """from_asus then to_asus round-trips within rounding tolerance."""

        source = (min(r, scale), min(g, scale), min(b, scale))
        color = Color.from_asus(*source, scale=scale)
        result = color.to_asus(scale=scale)
        for original, restored in zip(source, result, strict=True):
            assert abs(original - restored) <= 1

    def test_with_brightness(self) -> None:
        """with_brightness returns a copy with the new brightness."""

        color = Color(255, 128, 0, 200)
        dimmed = color.with_brightness(50)
        assert dimmed.brightness == 50
        assert (dimmed.red, dimmed.green, dimmed.blue) == (255, 128, 0)
        assert color.brightness == 200

    def test_with_brightness_clamped(self) -> None:
        """with_brightness clamps the new brightness."""

        assert Color().with_brightness(999).brightness == COLOR_SCALE

    def test_blend_empty(self) -> None:
        """Blending nothing yields the default color."""

        assert Color.blend([]) == Color()

    def test_blend(self) -> None:
        """Blending averages hue and keeps the peak brightness."""

        colors = [Color(200, 0, 0, 100), Color(0, 200, 0, 250)]
        blended = Color.blend(colors)
        assert blended.red == 100
        assert blended.green == 100
        assert blended.blue == 0
        assert blended.brightness == 250


class TestParseDump:
    """Tests for parse_colors / dump_colors."""

    @pytest.mark.parametrize("raw", [None, "", "   "])
    def test_parse_empty(self, raw: str | None) -> None:
        """Empty input yields an empty list."""

        assert parse_colors(raw, scale=COLOR_SCALE_ASUS_DAY) == []

    def test_parse_groups_of_three(self) -> None:
        """Channels are grouped into colors of three; remainder dropped."""

        colors = parse_colors("10,0,64,0,0,32,5", scale=COLOR_SCALE_ASUS_DAY)
        assert len(colors) == 2

    def test_parse_invalid_channel(self) -> None:
        """Non-numeric channels fall back to zero."""

        colors = parse_colors("x,y,z", scale=COLOR_SCALE_ASUS_DAY)
        assert colors == [Color(0, 0, 0, 0)]

    def test_dump_round_trip(self) -> None:
        """dump_colors reverses parse_colors within tolerance."""

        raw = "10,0,64,64,32,16"
        colors = parse_colors(raw, scale=COLOR_SCALE_ASUS_DAY)
        dumped = dump_colors(colors, scale=COLOR_SCALE_ASUS_DAY)
        restored = [int(value) for value in dumped.split(",")]
        original = [int(value) for value in raw.split(",")]
        for was, now in zip(original, restored, strict=True):
            assert abs(was - now) <= 1

    def test_dump_empty(self) -> None:
        """Dumping no colors yields an empty string."""

        assert dump_colors([], scale=COLOR_SCALE_ASUS_DAY) == ""
