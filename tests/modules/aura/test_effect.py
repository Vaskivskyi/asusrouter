"""Tests for the Aura effect color helpers."""

from __future__ import annotations

from asusrouter.modules.aura.effect import (
    apply_brightness,
    apply_color,
    default_colors,
    fit_zones,
)
from asusrouter.tools.color import Color


class TestDefaultColors:
    """Tests for default_colors."""

    def test_zero(self) -> None:
        """No zones yields no colors."""

        assert default_colors(0) == []
        assert default_colors(-1) == []

    def test_repeats_pattern(self) -> None:
        """The default pattern repeats across zones."""

        colors = default_colors(5)
        assert len(colors) == 5
        assert colors[0] == colors[4]  # pattern length is 4


class TestFitZones:
    """Tests for fit_zones."""

    def test_truncate(self) -> None:
        """Extra colors are dropped."""

        colors = [Color(255, 0, 0), Color(0, 255, 0), Color(0, 0, 255)]
        assert fit_zones(colors, 2) == colors[:2]

    def test_pad(self) -> None:
        """Missing colors are padded from the defaults."""

        fitted = fit_zones([Color(255, 0, 0)], 3)
        assert len(fitted) == 3
        assert fitted[0] == Color(255, 0, 0)

    def test_zero_zones(self) -> None:
        """A zone count of zero returns the list unchanged."""

        colors = [Color(255, 0, 0)]
        assert fit_zones(colors, 0) == colors


class TestApplyColor:
    """Tests for apply_color."""

    def test_none(self) -> None:
        """No color leaves the list unchanged."""

        colors = [Color(1, 2, 3, 100)]
        assert apply_color(colors, None) == colors

    def test_single_all_zones(self) -> None:
        """A single color without a zone applies to all, keeping brightness."""

        colors = [Color(0, 0, 0, 100), Color(0, 0, 0, 200)]
        result = apply_color(colors, Color(255, 0, 0))
        assert result[0] == Color(255, 0, 0, 100)
        assert result[1] == Color(255, 0, 0, 200)

    def test_single_one_zone(self) -> None:
        """A single color with a zone applies only there."""

        colors = [Color(0, 0, 0, 100), Color(0, 0, 0, 200)]
        result = apply_color(colors, Color(255, 0, 0), zone=1)
        assert result[0] == Color(0, 0, 0, 100)
        assert result[1] == Color(255, 0, 0, 200)

    def test_single_zone_out_of_range(self) -> None:
        """An out-of-range zone falls back to all zones."""

        colors = [Color(0, 0, 0, 100)]
        result = apply_color(colors, Color(255, 0, 0), zone=5)
        assert result[0] == Color(255, 0, 0, 100)

    def test_list_cycles(self) -> None:
        """A color list is applied cyclically across the zones."""

        colors = [Color(0, 0, 0, 10)] * 3
        palette = [Color(255, 0, 0), Color(0, 255, 0)]
        result = apply_color(colors, palette)
        assert result[0].red == 255
        assert result[1].green == 255
        assert result[2].red == 255  # cycles back
        assert all(color.brightness == 10 for color in result)

    def test_empty_list(self) -> None:
        """An empty color list leaves the zones unchanged."""

        colors = [Color(1, 2, 3, 100)]
        assert apply_color(colors, []) == colors


class TestApplyBrightness:
    """Tests for apply_brightness."""

    def test_none(self) -> None:
        """No brightness leaves the list unchanged."""

        colors = [Color(1, 2, 3, 100)]
        assert apply_brightness(colors, None) == colors

    def test_all_zones(self) -> None:
        """Brightness without a zone applies to all."""

        colors = [Color(1, 0, 0, 10), Color(0, 1, 0, 20)]
        result = apply_brightness(colors, 200)
        assert all(color.brightness == 200 for color in result)

    def test_one_zone(self) -> None:
        """Brightness with a zone applies only there."""

        colors = [Color(1, 0, 0, 10), Color(0, 1, 0, 20)]
        result = apply_brightness(colors, 200, zone=0)
        assert result[0].brightness == 200
        assert result[1].brightness == 20

    def test_zone_out_of_range(self) -> None:
        """An out-of-range zone falls back to all zones."""

        colors = [Color(1, 0, 0, 10)]
        result = apply_brightness(colors, 200, zone=9)
        assert result[0].brightness == 200
