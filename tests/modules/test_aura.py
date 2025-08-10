"""Tests for the Aura module."""

from typing import Any
from unittest import mock
from unittest.mock import AsyncMock, MagicMock, patch

from asusrouter.modules.aura import (
    DEFAULT_AURA_SCHEME,
    DEFAULT_COLOR_PATTERN,
    AsusAura,
    AsusAuraColor,
    DefaultAuraColor,
    get_default_aura_color,
    get_scheme_from_state,
    process_aura,
    set_brightness,
    set_color,
    set_state,
)
from asusrouter.modules.color import ColorRGB, ColorRGBB
from asusrouter.modules.data import AsusData, AsusDataState
from asusrouter.modules.endpoint import EndpointTools
from asusrouter.modules.identity import AsusDevice
import pytest


@pytest.mark.parametrize(
    ("enum_member", "expected_value"),
    [
        (AsusAura.UNKNOWN, -999),
        (AsusAura.ON, -1),
        (AsusAura.OFF, 0),
        (AsusAura.GRADIENT, 1),
        (AsusAura.STATIC, 2),
        (AsusAura.BREATHING, 3),
        (AsusAura.EVOLUTION, 4),
        (AsusAura.RAINBOW, 5),
        (AsusAura.WAVE, 6),
        (AsusAura.MARQUEE, 7),
    ],
)
def test_asus_aura(enum_member: AsusAura, expected_value: int) -> None:
    """Test AsusAura enum."""

    assert enum_member.value == expected_value


def test_asus_aura_members() -> None:
    """Test AsusAura members."""

    expected_members = {
        "UNKNOWN": -999,
        "ON": -1,
        "OFF": 0,
        "GRADIENT": 1,
        "STATIC": 2,
        "BREATHING": 3,
        "EVOLUTION": 4,
        "RAINBOW": 5,
        "WAVE": 6,
        "MARQUEE": 7,
    }
    actual_members = {member.name: member.value for member in AsusAura}
    assert actual_members == expected_members


@pytest.mark.parametrize(
    ("enum_member", "expected_value"),
    [
        (AsusAuraColor.GRADIENT, 1),
        (AsusAuraColor.STATIC, 2),
        (AsusAuraColor.BREATHING, 3),
        (AsusAuraColor.MARQUEE, 7),
    ],
)
def test_asus_aura_color(
    enum_member: AsusAuraColor, expected_value: int
) -> None:
    """Test AsusAuraColor enum."""

    assert enum_member.value == expected_value


def test_asus_aura_color_members() -> None:
    """Test AsusAuraColor members."""

    expected_members = {
        "GRADIENT": 1,
        "STATIC": 2,
        "BREATHING": 3,
        "MARQUEE": 7,
    }
    actual_members = {member.name: member.value for member in AsusAuraColor}
    assert actual_members == expected_members


@pytest.mark.parametrize(
    ("enum_member", "expected_value"),
    [
        (DefaultAuraColor.COLOR1, ColorRGBB((20, 0, 128))),
        (DefaultAuraColor.COLOR2, ColorRGBB((110, 0, 100))),
        (DefaultAuraColor.COLOR3, ColorRGBB((128, 0, 80))),
    ],
)
def test_default_aura_color(
    enum_member: DefaultAuraColor, expected_value: ColorRGBB
) -> None:
    """Test DefaultAuraColor enum."""

    assert enum_member.value == expected_value


def test_default_aura_color_members() -> None:
    """Test DefaultAuraColor members."""

    expected_members = {
        "COLOR1": ColorRGBB((20, 0, 128)),
        "COLOR2": ColorRGBB((110, 0, 100)),
        "COLOR3": ColorRGBB((128, 0, 80)),
    }
    actual_members = {member.name: member.value for member in DefaultAuraColor}
    assert actual_members == expected_members


def test_default_color_pattern() -> None:
    """Test that DEFAULT_COLOR_PATTERN tuple is correct."""

    expected_colors = (
        DefaultAuraColor.COLOR1,
        DefaultAuraColor.COLOR2,
        DefaultAuraColor.COLOR3,
        DefaultAuraColor.COLOR2,
    )
    assert expected_colors == DEFAULT_COLOR_PATTERN


def test_default_aura_scheme() -> None:
    """Test that DEFAULT_AURA_SCHEME is correct."""

    assert DEFAULT_AURA_SCHEME == AsusAura.STATIC


@pytest.mark.parametrize(
    ("zones", "expected_colors"),
    [
        (1, (ColorRGBB((20, 0, 128)),)),
        (2, (ColorRGBB((20, 0, 128)), ColorRGBB((110, 0, 100)))),
        (
            3,
            (
                ColorRGBB((20, 0, 128)),
                ColorRGBB((110, 0, 100)),
                ColorRGBB((128, 0, 80)),
            ),
        ),
        (
            4,
            (
                ColorRGBB((20, 0, 128)),
                ColorRGBB((110, 0, 100)),
                ColorRGBB((128, 0, 80)),
                ColorRGBB((110, 0, 100)),
            ),
        ),
        (
            5,
            (
                ColorRGBB((20, 0, 128)),
                ColorRGBB((110, 0, 100)),
                ColorRGBB((128, 0, 80)),
                ColorRGBB((110, 0, 100)),
                ColorRGBB((20, 0, 128)),
            ),
        ),
    ],
)
def test_get_default_aura_color(
    zones: int, expected_colors: tuple[ColorRGBB, ...]
) -> None:
    """Test get_default_aura_color function with different zone numbers."""

    result = get_default_aura_color(zones)
    assert result == expected_colors


@pytest.mark.parametrize(
    ("aura_state", "expected_scheme"),
    [
        # Known values
        ({"scheme": AsusAura.GRADIENT.value}, AsusAura.GRADIENT),
        ({"scheme": AsusAura.STATIC.value}, AsusAura.STATIC),
        ({"scheme": AsusAura.UNKNOWN.value}, DEFAULT_AURA_SCHEME),
        ({"scheme": AsusAura.ON.value}, DEFAULT_AURA_SCHEME),
        ({"scheme": AsusAura.OFF.value}, DEFAULT_AURA_SCHEME),
        ({"scheme_prev": AsusAura.BREATHING.value}, AsusAura.BREATHING),
        ({"scheme_prev": AsusAura.EVOLUTION.value}, AsusAura.EVOLUTION),
        ({"scheme_prev": AsusAura.UNKNOWN.value}, DEFAULT_AURA_SCHEME),
        ({"scheme_prev": AsusAura.ON.value}, DEFAULT_AURA_SCHEME),
        ({"scheme_prev": AsusAura.OFF.value}, DEFAULT_AURA_SCHEME),
        (
            {
                "scheme": AsusAura.UNKNOWN.value,
                "scheme_prev": AsusAura.RAINBOW.value,
            },
            AsusAura.RAINBOW,
        ),
        (
            {"scheme": AsusAura.ON.value, "scheme_prev": AsusAura.WAVE.value},
            AsusAura.WAVE,
        ),
        ({}, DEFAULT_AURA_SCHEME),
        # Random values
        ({"scheme": 100}, DEFAULT_AURA_SCHEME),
        ({"scheme": None}, DEFAULT_AURA_SCHEME),
        ({"scheme": "unknown"}, DEFAULT_AURA_SCHEME),
    ],
)
def test_get_scheme_from_state(
    aura_state: dict[str, Any], expected_scheme: AsusAura
) -> None:
    """Test get_scheme_from_state function with different aura states."""

    result = get_scheme_from_state(aura_state)
    assert result == expected_scheme


@pytest.mark.parametrize(
    ("initial_colors", "color_to_set", "zone", "zones", "expected_colors"),
    [
        # Single color to a specific zone
        (
            [ColorRGBB((0, 0, 0)), ColorRGBB((0, 0, 0))],
            ColorRGB((255, 0, 0)),
            1,
            None,
            [ColorRGBB((0, 0, 0)), ColorRGBB((255, 0, 0))],
        ),
        # Single color to all zones
        (
            [ColorRGBB((0, 0, 0)), ColorRGBB((0, 0, 0))],
            ColorRGB((255, 0, 0)),
            None,
            None,
            [ColorRGBB((255, 0, 0)), ColorRGBB((255, 0, 0))],
        ),
        # Multiple colors to all zones
        (
            [ColorRGBB((0, 0, 0)), ColorRGBB((0, 0, 0)), ColorRGBB((0, 0, 0))],
            [ColorRGB((255, 0, 0)), ColorRGB((0, 255, 0))],
            None,
            None,
            [
                ColorRGBB((255, 0, 0)),
                ColorRGBB((0, 255, 0)),
                ColorRGBB((255, 0, 0)),
            ],
        ),
        # No new color defined
        (
            [ColorRGBB((0, 0, 0)), ColorRGBB((0, 0, 0))],
            None,
            None,
            None,
            [ColorRGBB((0, 0, 0)), ColorRGBB((0, 0, 0))],
        ),
        # Zones parameter provided
        (
            [ColorRGBB((0, 0, 0)), ColorRGBB((0, 0, 0)), ColorRGBB((0, 0, 0))],
            ColorRGB((255, 0, 0)),
            None,
            2,
            [
                ColorRGBB((255, 0, 0)),
                ColorRGBB((255, 0, 0)),
                ColorRGBB((0, 0, 0)),
            ],
        ),
        # Wrong initial colors (less than zones)
        (
            [ColorRGBB((0, 0, 0)), ColorRGBB((0, 0, 0))],
            ColorRGB((255, 0, 0)),
            None,
            3,
            [
                ColorRGBB((255, 0, 0)),
                ColorRGBB((255, 0, 0)),
                ColorRGBB((255, 0, 0)),
            ],
        ),
        (
            [ColorRGBB((0, 0, 0)), ColorRGBB((0, 0, 0))],
            [ColorRGB((255, 0, 0)), ColorRGB((0, 255, 0))],
            None,
            3,
            [
                ColorRGBB((255, 0, 0)),
                ColorRGBB((0, 255, 0)),
                ColorRGBB((255, 0, 0)),
            ],
        ),
        # Wrong color to set
        (
            [ColorRGBB((0, 0, 0)), ColorRGBB((0, 0, 0))],
            "wrong",
            None,
            None,
            [ColorRGBB((0, 0, 0)), ColorRGBB((0, 0, 0))],
        ),
        (
            [ColorRGBB((255, 0, 0)), ColorRGBB((0, 255, 0))],
            ["wrong", "wrong"],
            None,
            None,
            [ColorRGBB((255, 0, 0)), ColorRGBB((0, 255, 0))],
        ),
    ],
)
def test_set_color(
    initial_colors: list[ColorRGBB],
    color_to_set: ColorRGB | list[ColorRGB] | None,
    zone: int | None,
    zones: int | None,
    expected_colors: list[ColorRGBB],
) -> None:
    """Test set_color function."""

    set_color(initial_colors, color_to_set, zone, zones)
    assert initial_colors == expected_colors


@pytest.mark.parametrize(
    ("initial_colors", "brightness", "zone", "expected_colors"),
    [
        # No brightness
        (
            [ColorRGBB((255, 0, 0)), ColorRGBB((0, 255, 0))],
            None,
            None,
            [ColorRGBB((255, 0, 0)), ColorRGBB((0, 255, 0))],
        ),
        # Brightness & no zone
        (
            [ColorRGBB((255, 0, 0)), ColorRGBB((0, 255, 0))],
            50,
            None,
            [ColorRGBB((255, 0, 0), 50), ColorRGBB((0, 255, 0), 50)],
        ),
        # Brightness & zone
        (
            [ColorRGBB((255, 0, 0)), ColorRGBB((0, 255, 0))],
            50,
            1,
            [ColorRGBB((255, 0, 0)), ColorRGBB((0, 255, 0), 50)],
        ),
        # Too high brightness
        (
            [ColorRGBB((255, 0, 0), 255), ColorRGBB((0, 255, 0), 255)],
            256,
            1,
            [ColorRGBB((255, 0, 0), 255), ColorRGBB((0, 255, 0), 255)],
        ),
        # Wrong brightness
        (
            [ColorRGBB((255, 0, 0), 255), ColorRGBB((0, 255, 0), 255)],
            "wrong",
            1,
            [ColorRGBB((255, 0, 0), 255), ColorRGBB((0, 255, 0), 255)],
        ),
        # Wrong zone
        (
            [ColorRGBB((255, 0, 0), 255), ColorRGBB((0, 255, 0), 255)],
            50,
            "wrong",
            [ColorRGBB((255, 0, 0), 50), ColorRGBB((0, 255, 0), 50)],
        ),
    ],
)
def test_set_brightness(
    initial_colors: list[ColorRGBB],
    brightness: int | None,
    zone: int | None,
    expected_colors: list[ColorRGBB],
) -> None:
    """Test set_brightness function."""

    set_brightness(initial_colors, brightness, zone)

    for color, expected in zip(initial_colors, expected_colors):
        assert color.brightness == expected.brightness


@pytest.mark.asyncio
@patch("asusrouter.modules.aura.get_arguments")
@patch("asusrouter.modules.aura.get_scheme_from_state")
@patch("asusrouter.modules.aura.set_color")
@patch("asusrouter.modules.aura.set_brightness")
async def test_set_state(
    mock_set_brightness: mock.Mock,
    mock_set_color: mock.Mock,
    mock_get_scheme_from_state: mock.Mock,
    mock_get_arguments: mock.Mock,
) -> None:
    """Test set_state function with different scenarios."""

    # Mock callback
    mock_callback = AsyncMock(return_value=True)

    # Constants
    default_get_arguments: dict[str, Any] = {
        "color": "color",
        "brightness": "brightness",
        "zone": "zone",
    }
    default_get_arguments_args = ("color", "brightness", "zone")

    # --- CASE 1: Test with no identity provided
    result = await set_state(mock_callback, AsusAura.ON)

    # Check the result
    assert result is False
    mock_callback.assert_not_called()
    mock_set_color.assert_not_called()
    mock_set_brightness.assert_not_called()
    mock_get_scheme_from_state.assert_not_called()

    # Reset the mock
    mock_callback.reset_mock()

    # --- CASE 2: Test with no color support
    mock_get_arguments.return_value = default_get_arguments
    mock_identity = MagicMock(spec=AsusDevice)
    mock_identity.aura_zone = 2
    mock_aura_state = {"scheme": AsusAura.RAINBOW}
    mock_kwargs = {
        "color": ColorRGB((255, 0, 0)),
        "brightness": 50,
        "zone": 1,
        "identity": mock_identity,
        "router_state": {
            AsusData.AURA: AsusDataState(mock_aura_state),
        },
    }

    result = await set_state(
        callback=mock_callback,
        state=AsusAura.RAINBOW,
        **mock_kwargs,
    )

    # Check the result
    assert result is True
    mock_callback.assert_called_once_with(
        endpoint=EndpointTools.AURA,
        commands={"ledg_scheme": AsusAura.RAINBOW.value},
    )
    mock_set_color.assert_not_called()
    mock_set_brightness.assert_not_called()
    mock_get_scheme_from_state.assert_not_called()
    mock_get_arguments.assert_called_once_with(
        default_get_arguments_args, **mock_kwargs
    )

    # Reset the mock
    mock_callback.reset_mock()
    mock_get_arguments.reset_mock()

    # --- CASE 3: Test with no explicit state / AsusAura.ON
    mock_get_scheme_from_state.return_value = AsusAura.RAINBOW

    result = await set_state(
        callback=mock_callback,
        state=AsusAura.ON,
        **mock_kwargs,
    )

    # Check the result
    assert result is True
    mock_callback.assert_called_once_with(
        endpoint=EndpointTools.AURA,
        commands={"ledg_scheme": AsusAura.RAINBOW.value},
    )
    mock_set_color.assert_not_called()
    mock_set_brightness.assert_not_called()
    mock_get_scheme_from_state.assert_called_once_with(mock_aura_state)
    mock_get_arguments.assert_called_once_with(
        default_get_arguments_args, **mock_kwargs
    )

    # Reset the mock
    mock_callback.reset_mock()
    mock_get_arguments.reset_mock()

    # --- CASE 4: Test with proper color support


@pytest.mark.asyncio
@patch("asusrouter.modules.aura.get_arguments")
@patch("asusrouter.modules.aura.get_scheme_from_state")
@patch("asusrouter.modules.aura.set_color")
@patch("asusrouter.modules.aura.set_brightness")
@patch("asusrouter.modules.aura.get_default_aura_color")
async def test_set_state_with_color_support(
    mock_get_default_aura_color: mock.Mock,
    mock_set_brightness: mock.Mock,
    mock_set_color: mock.Mock,
    mock_get_scheme_from_state: mock.Mock,
    mock_get_arguments: mock.Mock,
) -> None:
    """Test set_state function with proper color support."""

    # Mock callback
    mock_callback = AsyncMock(return_value=True)

    # Constants
    default_get_arguments: tuple[Any, ...] = (
        ColorRGB((255, 0, 0)),
        50,
        1,
    )

    # Mock the get_arguments function
    mock_get_arguments.return_value = default_get_arguments

    # Mock the identity
    mock_identity = MagicMock(spec=AsusDevice)
    mock_identity.aura_zone = 2

    # Mock the aura state
    mock_aura_state = {
        "effect": {1: [ColorRGBB((0, 0, 0)), ColorRGBB((0, 0, 0))]}
    }

    # Mock the get_default_aura_color function
    mock_get_default_aura_color.return_value = [ColorRGBB((255, 255, 255))]

    # Mock the kwargs
    mock_kwargs = {
        "color": ColorRGB((255, 0, 0)),
        "brightness": 50,
        "zone": 1,
        "identity": mock_identity,
        "router_state": {
            AsusData.AURA: AsusDataState(mock_aura_state),
        },
    }

    # Test with proper color support
    result = await set_state(
        callback=mock_callback,
        state=AsusAura.STATIC,
        **mock_kwargs,
    )

    # Check the result
    assert result is True

    # Check the calls
    state_number = AsusAuraColor[AsusAura.STATIC.name].value
    colors = mock_aura_state["effect"].get(
        state_number, mock_get_default_aura_color.return_value
    )

    mock_set_color.assert_called_once_with(
        colors,
        mock_kwargs["color"],
        mock_kwargs["zone"],
        mock_identity.aura_zone,
    )
    mock_set_brightness.assert_called_once_with(
        colors, mock_kwargs["brightness"], mock_kwargs["zone"]
    )

    color_to_use = ",".join(
        [color_zone.to_rgb().__str__() for color_zone in colors]
    )
    mock_callback.assert_called_once_with(
        endpoint=EndpointTools.AURA,
        commands={
            "ledg_scheme": AsusAura.STATIC.value,
            "ledg_rgb": color_to_use,
        },
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("state", "kwargs", "expected_ledg_scheme", "expected_ledg_rgb"),
    [
        # Static, single color, no zone, no brightness
        (
            AsusAura.STATIC,
            {"color": ColorRGB((255, 0, 0))},
            AsusAura.STATIC.value,
            "128,0,0,128,0,0,128,0,0",
        ),
        # Marquee, multiple colors, no zone, no brightness
        (
            AsusAura.MARQUEE,
            {"color": [ColorRGB((255, 0, 0)), ColorRGB((0, 255, 0))]},
            AsusAura.MARQUEE.value,
            "128,0,0,0,128,0,128,0,0",
        ),
        # Gradient, single color, zone, no brightness
        (
            AsusAura.GRADIENT,
            {"color": ColorRGB((255, 0, 0)), "zone": 1},
            AsusAura.GRADIENT.value,
            "128,0,0,128,0,0,0,0,128",
        ),
        # Breathing, no color, no zone, brightness
        (
            AsusAura.BREATHING,
            {"brightness": 64},
            AsusAura.BREATHING.value,
            "64,0,0,0,64,0,0,0,64",
        ),
        # Static, no color, no zone, over brightness
        (
            AsusAura.STATIC,
            {"brightness": 255},
            AsusAura.STATIC.value,
            "128,0,0,0,128,0,0,0,128",
        ),
        # Marquee, no color, zone, brightness
        (
            AsusAura.MARQUEE,
            {"zone": 1, "brightness": 64},
            AsusAura.MARQUEE.value,
            "128,0,0,0,64,0,0,0,128",
        ),
        # No color support state
        (
            AsusAura.RAINBOW,
            {"brightness": 64},
            AsusAura.RAINBOW.value,
            "128,0,0,0,128,0,0,0,128",
        ),
    ],
)
async def test_set_state_final(
    state: AsusAura,
    kwargs: dict[str, Any],
    expected_ledg_scheme: int,
    expected_ledg_rgb: str,
) -> None:
    """Test set_state function for the final output."""

    mock_callback = AsyncMock(return_value=True)
    mock_identity = MagicMock(spec=AsusDevice)
    mock_identity.aura_zone = 3
    mock_aura_state: dict[str, Any] = {
        "effect": {
            state.value: [
                ColorRGB((128, 0, 0)),
                ColorRGB((0, 128, 0)),
                ColorRGB((0, 0, 128)),
            ]
        }
    }
    mock_kwargs = {
        **kwargs,
        "identity": mock_identity,
        "router_state": {
            AsusData.AURA: AsusDataState(mock_aura_state),
        },
    }

    result = await set_state(
        callback=mock_callback, state=state, **mock_kwargs
    )

    commands = {
        "ledg_scheme": expected_ledg_scheme,
    }
    if state.name in AsusAuraColor.__members__:
        commands["ledg_rgb"] = expected_ledg_rgb

    assert result is True
    mock_callback.assert_called_once_with(
        endpoint=EndpointTools.AURA,
        commands=commands,
    )


@pytest.mark.parametrize(
    ("input_data", "expected_output"),
    [
        # On, Marquee, 3 zones
        (
            {
                "AllLED": "1",
                "ledg_night_mode": "",
                "ledg_scheme": "7",
                "ledg_scheme_old": "2",
                "ledg_rgb0": "",
                "ledg_rgb1": "128,68,7,128,79,122,128,127,125",
                "ledg_rgb2": "128,0,6,8,128,0,0,8,128",
                "ledg_rgb3": "32,64,128,128,64,32,32,64,128",
                "ledg_rgb4": "",
                "ledg_rgb5": "",
                "ledg_rgb6": "",
                "ledg_rgb7": "0,128,11,0,4,128,128,0,11",
            },
            {
                "state": True,
                "night_mode": None,
                "scheme": AsusAura.MARQUEE,
                "scheme_prev": AsusAura.STATIC,
                "effect": {
                    0: None,
                    1: [
                        ColorRGBB((128, 68, 7)),
                        ColorRGBB((128, 79, 122)),
                        ColorRGBB((128, 127, 125)),
                    ],
                    2: [
                        ColorRGBB((128, 0, 6)),
                        ColorRGBB((8, 128, 0)),
                        ColorRGBB((0, 8, 128)),
                    ],
                    3: [
                        ColorRGBB((32, 64, 128)),
                        ColorRGBB((128, 64, 32)),
                        ColorRGBB((32, 64, 128)),
                    ],
                    4: None,
                    5: None,
                    6: None,
                    7: [
                        ColorRGBB((0, 128, 11)),
                        ColorRGBB((0, 4, 128)),
                        ColorRGBB((128, 0, 11)),
                    ],
                },
                "active": {
                    0: {"color": ColorRGBB((0, 128, 11)), "brightness": 128},
                    1: {"color": ColorRGBB((0, 4, 128)), "brightness": 128},
                    2: {"color": ColorRGBB((128, 0, 11)), "brightness": 128},
                    "color": ColorRGBB(
                        (42, 44, 50)
                    ),  # Average color of the active effect
                    "brightness": 128,
                },
                "zones": 3,
            },
        ),
        # Off, 2 zones
        (
            {
                "AllLED": "1",
                "ledg_night_mode": "",
                "ledg_scheme": "0",
                "ledg_scheme_old": "2",
                "ledg_rgb0": "",
                "ledg_rgb1": "128,68,7,128,79,122",
                "ledg_rgb2": "128,0,6,8,128,0",
                "ledg_rgb3": "32,64,128,128,64,32",
                "ledg_rgb4": "",
                "ledg_rgb5": "",
                "ledg_rgb6": "",
                "ledg_rgb7": "0,128,11,0,4,128",
            },
            {
                "state": False,
                "night_mode": None,
                "scheme": AsusAura.OFF,
                "scheme_prev": AsusAura.STATIC,
                "effect": {
                    0: None,
                    1: [
                        ColorRGBB((128, 68, 7)),
                        ColorRGBB((128, 79, 122)),
                    ],
                    2: [
                        ColorRGBB((128, 0, 6)),
                        ColorRGBB((8, 128, 0)),
                    ],
                    3: [
                        ColorRGBB((32, 64, 128)),
                        ColorRGBB((128, 64, 32)),
                    ],
                    4: None,
                    5: None,
                    6: None,
                    7: [
                        ColorRGBB((0, 128, 11)),
                        ColorRGBB((0, 4, 128)),
                    ],
                },
                "active": {},
                "zones": 2,
            },
        ),
        # Missing data
        (
            {},
            {
                "state": None,
                "night_mode": None,
                "scheme": AsusAura.UNKNOWN,
                "scheme_prev": AsusAura.UNKNOWN,
                "effect": {},
                "active": {},
                "zones": 0,
            },
        ),
    ],
)
def test_process_aura(
    input_data: dict[str, Any], expected_output: dict[str, Any]
) -> None:
    """Test process_aura function."""

    output = process_aura(input_data)
    assert output == expected_output


def test_process_aura_unknown(caplog: pytest.LogCaptureFixture) -> None:
    """Test process_aura function for unknown scheme log."""

    input_scheme = "unknown_1"
    input_scheme_prev = 123
    input_data = {
        "ledg_scheme": input_scheme,
        "ledg_scheme_old": input_scheme_prev,
    }

    with caplog.at_level("WARNING"):
        process_aura(input_data)

    # There should not be any log for non-numerical values
    # assert f"Unknown Aura scheme: `{input_scheme}`" in caplog.text
    assert f"Unknown Aura scheme: `{input_scheme_prev}`" in caplog.text
