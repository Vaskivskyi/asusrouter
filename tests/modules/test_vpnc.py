"""Tests for the vpnc module."""

from typing import Any
from unittest import mock

import pytest

from asusrouter.modules.data import AsusData, AsusDataState
from asusrouter.modules.led import AsusLED
from asusrouter.modules.openvpn import AsusOVPNClient
from asusrouter.modules.vpnc import (
    AsusVPNC,
    AsusVPNType,
    _find_vpnc_unit,
    _get_argument_clientlist,
    set_state,
    set_state_other,
    set_state_vpnc,
)
from asusrouter.modules.wireguard import AsusWireGuardClient


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("state", "expected_function"),
    [
        # Real states
        (AsusVPNC.ON, "set_state_vpnc"),
        (AsusOVPNClient.OFF, "set_state_other"),
        (AsusWireGuardClient.ON, "set_state_other"),
        # Wrong states
        (AsusLED, None),
        # Not states
        (1, None),
        ("string", None),
        (None, None),
    ],
)
async def test_set_state(
    state: AsusVPNC | AsusOVPNClient | AsusWireGuardClient,
    expected_function: str | None,
) -> None:
    """Test set_state."""

    # Mock the callback
    callback = mock.AsyncMock(return_value=True)

    # Mock kwargs
    kwargs = {"fake": "kwargs"}

    # Mock the set_state functions
    with (
        mock.patch(
            "asusrouter.modules.vpnc.set_state_vpnc"
        ) as set_state_vpnc_mock,
        mock.patch(
            "asusrouter.modules.vpnc.set_state_other"
        ) as set_state_other_mock,
    ):
        # Call set_state
        await set_state(callback, state, **kwargs)

        # Check which function was called
        if expected_function == "set_state_vpnc":
            set_state_vpnc_mock.assert_called_once_with(
                callback, state, **kwargs
            )
            set_state_other_mock.assert_not_called()

        elif expected_function == "set_state_other":
            set_state_other_mock.assert_called_once_with(
                callback, state, **kwargs
            )
            set_state_vpnc_mock.assert_not_called()

        else:
            set_state_vpnc_mock.assert_not_called()
            set_state_other_mock.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "state",
        "vpnc_unit",
        "router_state",
        "clientlist",
        "get_arguments_call",
        "get_clientlist_call",
        "callback_call",
        "expected_result",
    ),
    [
        # Real state - this should pass
        (
            AsusVPNC.ON,
            1,
            {AsusData.VPNC_CLIENTLIST: AsusDataState("some_data")},
            "clientlist",
            True,
            True,
            True,
            True,
        ),
        # Clientlist not found - this will fail on checking the clientlist
        (
            AsusVPNC.ON,
            1,
            {AsusData.VPNC_CLIENTLIST: AsusDataState("some_data")},
            None,
            True,
            True,
            False,
            False,
        ),
        # Wrong state of VPNC - should fail when mapping the state to a service
        (
            AsusVPNC.ERROR,
            1,
            {AsusData.VPNC_CLIENTLIST: AsusDataState("some_data")},
            "clientlist",
            True,
            False,
            False,
            False,
        ),
        # Non-VPCN state - should fail imidiately
        (
            AsusLED.ON,
            1,
            {AsusData.VPNC_CLIENTLIST: AsusDataState("some_data")},
            "clientlist",
            False,
            False,
            False,
            False,
        ),
        # No state - should fail imidiately
        (None, 1, "fake_state", "clientlist", False, False, False, False),
        # VPNC unit issues - should fail when getting the arguments
        (
            AsusVPNC.ON,
            None,
            "fake_state",
            "clientlist",
            True,
            False,
            False,
            False,
        ),
        (
            AsusVPNC.ON,
            "fake_unit",
            "fake_state",
            "clientlist",
            True,
            False,
            False,
            False,
        ),
        # Router state issues - should fail when getting the clientlist
        (AsusVPNC.ON, 1, None, "clientlist", True, False, False, False),
    ],
)
async def test_set_state_vpnc_failing(  # noqa: PLR0913
    state: AsusVPNC | None,
    vpnc_unit: int | None,
    router_state: str | None,
    clientlist: str | None,
    get_arguments_call: bool,
    get_clientlist_call: bool,
    callback_call: bool,
    expected_result: bool,
) -> None:
    """Test set_state_vpnc failing."""

    # Mock the callback
    callback = mock.AsyncMock(return_value=True)

    # Collect kwargs
    kwargs = {}
    if vpnc_unit is not None:
        kwargs["vpnc_unit"] = vpnc_unit
    if router_state is not None:
        kwargs["router_state"] = router_state

    with (
        mock.patch(
            "asusrouter.modules.vpnc.get_arguments", return_value=vpnc_unit
        ) as get_arguments_mock,
        mock.patch(
            "asusrouter.modules.vpnc._get_argument_clientlist",
            return_value=clientlist,
        ) as get_argument_clientlist_mock,
        mock.patch.dict(
            "asusrouter.modules.vpnc.VPNC_STATE_MAPPING",
            values={AsusVPNC.ON: ("restart_vpnc", 1)},
        ),
    ):
        # Get the result
        result = await set_state_vpnc(callback, state=state, **kwargs)

        # Check the result
        assert result is expected_result

        # Check the calls
        # get_arguments
        if get_arguments_call:
            get_arguments_mock.assert_called_once_with("vpnc_unit", **kwargs)
        else:
            get_arguments_mock.assert_not_called()

        # _get_argument_clientlist
        if get_clientlist_call:
            get_argument_clientlist_mock.assert_called_once()
        else:
            get_argument_clientlist_mock.assert_not_called()

        # callback
        if callback_call:
            callback.assert_called_once_with(
                service="restart_vpnc",
                arguments={
                    "vpnc_unit": vpnc_unit,
                    "vpnc_clientlist": "clientlist",
                },
                apply=True,
                expect_modify=False,
            )
        else:
            callback.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "state",
        "vpn_id",
        "vpnc_data",
        "get_arguments_call",
        "find_vpnc_unit_call",
        "set_state_vpnc_call",
        "expected_state",
        "expected_result",
    ),
    [
        # Real state - this should pass
        (
            AsusOVPNClient.ON,
            1,
            "some_data",
            True,
            True,
            True,
            AsusVPNC.ON,
            True,
        ),
        (
            AsusOVPNClient.OFF,
            1,
            "some_data",
            True,
            True,
            True,
            AsusVPNC.OFF,
            True,
        ),
        # Wrong state
        (
            AsusOVPNClient.ERROR,
            1,
            "some_data",
            False,
            False,
            False,
            None,
            False,
        ),
        # Non-VPN state
        (
            AsusLED.ON,
            1,
            "some_data",
            False,
            False,
            False,
            None,
            False,
        ),
        # VPN id issues
        (
            AsusOVPNClient.ON,
            None,
            "some_data",
            True,
            False,
            False,
            None,
            False,
        ),
    ],
)
async def test_set_state_other(  # noqa: PLR0913
    state: AsusOVPNClient | AsusWireGuardClient,
    vpn_id: int | None,
    vpnc_data: str | None,
    get_arguments_call: bool,
    find_vpnc_unit_call: bool,
    set_state_vpnc_call: bool,
    expected_state: AsusVPNC | None,
    expected_result: bool,
) -> None:
    """Test set_state_other."""

    # Mock the callback
    callback = mock.AsyncMock(return_value=True)

    # Collect kwargs
    router_state = None
    kwargs = {}
    if vpn_id is not None:
        kwargs["id"] = vpn_id
    if vpnc_data is not None:
        router_state = {AsusData.VPNC: AsusDataState(vpnc_data)}
        kwargs["router_state"] = router_state

    with (
        mock.patch(
            "asusrouter.modules.vpnc.get_arguments", return_value=vpn_id
        ) as get_arguments_mock,
        mock.patch(
            "asusrouter.modules.vpnc._find_vpnc_unit"
        ) as find_vpnc_unit_mock,
        mock.patch.dict(
            "asusrouter.modules.vpnc.OTHER_STATE_MAPPING",
            values={AsusOVPNClient.ON: AsusVPNC.ON},
        ),
        mock.patch(
            "asusrouter.modules.vpnc.set_state_vpnc", return_value=True
        ) as set_state_vpnc_mock,
    ):
        # Get the result
        result = await set_state_other(callback, state=state, **kwargs)

        # Check the result
        assert result is expected_result

        # Check the calls
        # get_arguments
        if get_arguments_call:
            get_arguments_mock.assert_called_once_with("id", **kwargs)
        else:
            get_arguments_mock.assert_not_called()

        # _find_vpnc_unit
        if find_vpnc_unit_call:
            find_vpnc_unit_mock.assert_called_once_with(
                vpnc_data=vpnc_data, client_type=state, client_id=vpn_id
            )
        else:
            find_vpnc_unit_mock.assert_not_called()

        # set_state_vpnc
        if set_state_vpnc_call:
            set_state_vpnc_mock.assert_called_once_with(
                callback=callback,
                state=expected_state,
                vpnc_unit=find_vpnc_unit_mock.return_value,
                expect_modify=False,
                router_state=router_state,
            )
        else:
            set_state_vpnc_mock.assert_not_called()


@pytest.mark.parametrize(
    ("clientlist", "vpnc_unit", "state", "expected_result"),
    [
        # Test when clientlist, vpnc_unit, or state is None
        (None, 1, 1, None),
        ("something", None, 1, None),
        ("something", 1, None, None),
        # Test when clientlist is empty
        ("", 1, 1, None),
        # Test when vpnc_unit is out of range
        ("wrong<format<data", 3, 1, None),
        # Test when clientlist, vpnc_unit, and state are valid
        (
            "client1>param1>param2>param3>param4>param5<client2",
            0,
            1,
            "client1>param1>param2>param3>param4>1<client2",
        ),
        (
            "client1<client2>param1>param2>param3>param4>param5",
            1,
            1,
            "client1<client2>param1>param2>param3>param4>1",
        ),
    ],
)
def test_get_argument_clientlist(
    clientlist: str | None,
    vpnc_unit: int | None,
    state: int | None,
    expected_result: str | None,
) -> None:
    """Test _get_argument_clientlist."""

    # Get the result
    result = _get_argument_clientlist(clientlist, vpnc_unit, state)

    # Check the result
    assert result == expected_result


@pytest.mark.parametrize(
    ("vpnc_data", "client_type", "client_id", "expected_result"),
    [
        # Test when vpnc_data is None
        (None, AsusOVPNClient.CONNECTED, 1, None),
        # Test when client_type is not AsusOVPNClient or AsusWireGuardClient
        (
            {AsusVPNType.OPENVPN: {1: {"vpnc_unit": 1}}},
            "UnknownClientType",
            1,
            None,
        ),
        # Test when search_type is not in vpnc_data
        (
            {AsusVPNType.WIREGUARD: {1: {"vpnc_unit": 1}}},
            AsusOVPNClient.CONNECTED,
            1,
            None,
        ),
        # Test when client_id is not in vpnc_data[search_type]
        (
            {AsusVPNType.OPENVPN: {2: {"vpnc_unit": 1}}},
            AsusOVPNClient.DISCONNECTED,
            1,
            None,
        ),
        # Test when all inputs are valid
        (
            {AsusVPNType.OPENVPN: {1: {"vpnc_unit": 1}}},
            AsusOVPNClient.CONNECTED,
            1,
            1,
        ),
        (
            {AsusVPNType.WIREGUARD: {1: {"vpnc_unit": 1}}},
            AsusWireGuardClient.ON,
            1,
            1,
        ),
    ],
)
def test_find_vpnc_unit(
    vpnc_data: dict[AsusVPNType, dict[int, dict[str, Any]]],
    client_type: AsusOVPNClient | AsusWireGuardClient,
    client_id: int,
    expected_result: int | None,
) -> None:
    """Test _find_vpnc_unit."""

    # Get the result
    result = _find_vpnc_unit(vpnc_data, client_type, client_id)

    # Check the result
    assert result == expected_result
