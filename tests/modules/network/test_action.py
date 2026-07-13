"""Tests for the network action module."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

from asusrouter.const import AR_CALL_RUN_ACTION
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.network.action import (
    ARNetworkAction,
    find_handle_by_ssid,
    run_action,
)
from asusrouter.modules.network.enums import (
    ARNetworkBackend,
    ARNetworkField,
    ARNetworkType,
)
from asusrouter.modules.network.handle import ARNetworkHandle
from asusrouter.modules.nvram import ARNvramType
from asusrouter.modules.service.action import ARServiceResult
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.identifiers import Ssid


def _enc(text: str) -> str:
    """Char-encode `<`/`>` as the router does."""

    return text.replace("<", "&#60").replace(">", "&#62")


_SDN_RL = _enc("<1>MAINFH>1>0>0>2<3>Customized>1>0>0>4")

_SDN_HANDLE = ARNetworkHandle(
    backend=ARNetworkBackend.SDN, sdn_idx=3, ap_prefix="apg", ap_idx=4
)
_LEGACY_HANDLE = ARNetworkHandle(
    backend=ARNetworkBackend.LEGACY, units=((0, 1),)
)


class TestFindHandleBySsid:
    """Tests for find_handle_by_ssid."""

    _NETWORKS: dict[ARNetworkType, list[dict[ARNetworkField, Any]]] = {
        ARNetworkType.MAINFH: [
            {
                ARNetworkField.SSID: Ssid("Home"),
                ARNetworkField.HANDLE: _SDN_HANDLE,
            }
        ],
        ARNetworkType.GUEST: [
            {
                ARNetworkField.SSID: Ssid("Guest"),
                ARNetworkField.HANDLE: _LEGACY_HANDLE,
            },
            {ARNetworkField.SSID: Ssid("NoHandle")},
        ],
    }

    def test_found_by_ssid_object(self) -> None:
        """A matching Ssid object returns the profile's handle."""

        assert (
            find_handle_by_ssid(self._NETWORKS, Ssid("Guest"))
            is _LEGACY_HANDLE
        )

    def test_found_by_str(self) -> None:
        """A matching plain string returns the profile's handle."""

        assert find_handle_by_ssid(self._NETWORKS, "Home") is _SDN_HANDLE

    def test_not_found(self) -> None:
        """An unknown SSID returns None."""

        assert find_handle_by_ssid(self._NETWORKS, "Missing") is None

    def test_match_without_handle(self) -> None:
        """A matching profile that carries no handle returns None."""

        assert find_handle_by_ssid(self._NETWORKS, "NoHandle") is None


class TestARNetworkAction:
    """Tests for ARNetworkAction."""

    def test_stores_handle_and_state(self) -> None:
        """The handle and desired state are stored as given."""

        action = ARNetworkAction(_LEGACY_HANDLE, True)
        assert action.handle is _LEGACY_HANDLE
        assert action.state is True

    def test_equality_and_hash(self) -> None:
        """Actions are equal by handle and state."""

        base = ARNetworkAction(_LEGACY_HANDLE, True)
        assert base == ARNetworkAction(_LEGACY_HANDLE, True)
        assert hash(base) == hash(ARNetworkAction(_LEGACY_HANDLE, True))
        assert base != ARNetworkAction(_LEGACY_HANDLE, False)
        assert base != ARNetworkAction(_SDN_HANDLE, True)
        assert base != object()

    def test_registered(self) -> None:
        """The action resolves a run_action callable via the registry."""

        assert (
            ARCallReg.get_callable(
                ARNetworkAction(_LEGACY_HANDLE, True), AR_CALL_RUN_ACTION
            )
            is run_action
        )


class TestRunAction:
    """Tests for network run_action."""

    async def test_sdn_reads_then_pushes(self) -> None:
        """SDN fetches sdn_rl, then pushes the toggled list and apg enable."""

        get_data_callback = AsyncMock(
            return_value={ARNvramType.SDN_RL: _SDN_RL}
        )
        raw_callback = AsyncMock(return_value="NOT MODIFIED")
        action = ARNetworkAction(_SDN_HANDLE, True)

        result = await run_action(
            AsyncMock(),
            action,
            get_data_callback=get_data_callback,
            raw_callback=raw_callback,
        )

        assert result.success is True
        # sdn_rl fetched via the data pipeline
        get_data_callback.assert_awaited_once_with(ARNvramType.SDN_RL)
        # request pushed via the raw callback
        push = raw_callback.await_args.kwargs
        assert push["endpoint"] is AREndpoint.PUSH_DATA
        assert (
            '"rc_service":"restart_wireless;restart_sdn 3;"'
            in (push["request"])
        )
        assert '"apg4_enable":1' in push["request"]

    async def test_sdn_missing_list_fails(self) -> None:
        """A missing sdn_rl fails without a push."""

        get_data_callback = AsyncMock(return_value={})
        raw_callback = AsyncMock()
        result = await run_action(
            AsyncMock(),
            ARNetworkAction(_SDN_HANDLE, True),
            get_data_callback=get_data_callback,
            raw_callback=raw_callback,
        )

        assert result == ARServiceResult(success=False)
        raw_callback.assert_not_awaited()

    async def test_sdn_no_data_callback_fails(self) -> None:
        """SDN without a data callback fails without a push."""

        raw_callback = AsyncMock()
        result = await run_action(
            AsyncMock(),
            ARNetworkAction(_SDN_HANDLE, True),
            raw_callback=raw_callback,
        )

        assert result == ARServiceResult(success=False)
        raw_callback.assert_not_awaited()

    async def test_sdn_non_dict_read_fails(self) -> None:
        """A non-dict nvram reply fails without a push."""

        get_data_callback = AsyncMock(return_value=None)
        raw_callback = AsyncMock()
        result = await run_action(
            AsyncMock(),
            ARNetworkAction(_SDN_HANDLE, True),
            get_data_callback=get_data_callback,
            raw_callback=raw_callback,
        )

        assert result == ARServiceResult(success=False)
        raw_callback.assert_not_awaited()

    async def test_legacy_pushes_via_callback(self) -> None:
        """Legacy builds its payload and pushes via the plain callback."""

        callback = AsyncMock(
            return_value={"run_service": "restart_wireless;restart_firewall"}
        )
        action = ARNetworkAction(_LEGACY_HANDLE, True)

        result = await run_action(callback, action)

        assert result.success is True
        push = callback.await_args.kwargs
        assert push["endpoint"] is AREndpoint.PUSH_DATA
        assert '"wl0.1_bss_enabled":1' in push["request"]
        assert '"wl0.1_expire":0' in push["request"]
