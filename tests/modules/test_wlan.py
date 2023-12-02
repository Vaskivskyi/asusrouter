"""Tests for the wlan module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from asusrouter.modules.wlan import (
    MAP_GWLAN,
    MAP_WLAN,
    AsusWLAN,
    Wlan,
    _nvram_request,
    gwlan_nvram_request,
    set_state,
    wlan_nvram_request,
)


@pytest.mark.parametrize(
    "wlan, guest, expected_request",
    [
        # No wlan specified
        (None, False, None),
        ([], False, None),
        (None, True, None),
        ([], True, None),
        # WLAN
        ([Wlan.FREQ_2G], False, "wl0_auth_mode_x,wl0_bw"),
        ([Wlan.FREQ_5G], False, "wl1_auth_mode_x,wl1_bw"),
        ([Wlan.FREQ_6G], False, "wl3_auth_mode_x,wl3_bw"),
        # GWLAN
        (
            [Wlan.FREQ_2G],
            True,
            "wl0.1_auth_mode_x,wl0.1_bw",
        ),
        (
            [Wlan.FREQ_5G],
            True,
            "wl1.1_auth_mode_x,wl1.1_bw",
        ),
        (
            [Wlan.FREQ_6G],
            True,
            "wl3.1_auth_mode_x,wl3.1_bw",
        ),
    ],
)
def test_nvram_request(wlan, guest, expected_request):
    """Test _nvram_request."""

    with patch("asusrouter.modules.wlan.nvram", return_value=expected_request), patch(
        "asusrouter.modules.wlan.MAP_WLAN",
        new_callable=lambda: [("wl{}_auth_mode_x"), ("wl{}_bw")],
    ):
        assert _nvram_request(wlan, MAP_WLAN, guest) == expected_request


def test_wlan_nvram_request():
    """Test wlan_nvram_request."""

    mock = MagicMock()
    with patch("asusrouter.modules.wlan._nvram_request", new=mock):
        wlan_nvram_request([Wlan.FREQ_2G])
        mock.assert_called_with([Wlan.FREQ_2G], MAP_WLAN)


def test_gwlan_nvram_request():
    """Test gwlan_nvram_request."""

    mock = MagicMock()
    with patch("asusrouter.modules.wlan._nvram_request", new=mock):
        gwlan_nvram_request([Wlan.FREQ_2G])
        mock.assert_called_with([Wlan.FREQ_2G], MAP_GWLAN, guest=True)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "state, api_type, api_id, expected_service, expected_arguments, expected_result",
    [
        # WLAN
        (AsusWLAN.ON, "wlan", 0, "restart_wireless", {"wl0_radio": 1}, True),
        (AsusWLAN.OFF, "wlan", 0, "restart_wireless", {"wl0_radio": 0}, True),
        # GWLAN
        (
            AsusWLAN.ON,
            "gwlan",
            0,
            "restart_wireless;restart_firewall",
            {"wl0_bss_enabled": 1, "wl0_expire": 0},
            True,
        ),
        (
            AsusWLAN.OFF,
            "gwlan",
            0,
            "restart_wireless;restart_firewall",
            {"wl0_bss_enabled": 0},
            True,
        ),
        # Invalid type
        (AsusWLAN.ON, "invalid", "invalid", None, None, False),
        # Missing api_type
        (AsusWLAN.ON, None, 0, None, None, False),
        # Missing api_id
        (AsusWLAN.ON, "wlan", None, None, None, False),
        # Missing both
        (AsusWLAN.ON, None, None, None, None, False),
    ],
)
async def test_set_state(
    state, api_type, api_id, expected_service, expected_arguments, expected_result
):
    """Test set_state."""

    # Mock the callback function to return True
    callback = AsyncMock(return_value=True)

    result = await set_state(callback, state, api_type=api_type, api_id=api_id)

    # Check if the callback was called with the expected arguments
    if expected_service:
        callback.assert_called_once_with(
            expected_service,
            arguments=expected_arguments,
            apply=True,
            expect_modify=False,
        )
    else:
        callback.assert_not_called()

    # Check if the function returned the expected result
    assert result == expected_result
