"""Tests for the DDNS action."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock

import pytest

from asusrouter.modules.ddns import action as action_module
from asusrouter.modules.ddns.action import ARDdnsAction, run_action
from asusrouter.modules.ddns.enums import (
    ARDdnsCommand,
    ARDdnsField,
    ARDdnsServer,
)
from asusrouter.modules.ddns.source import DDNS_REQUEST, ARDdnsSourceUniversal
from asusrouter.modules.endpoint import AREndpoint
from asusrouter.tools.identifiers import Hostname, Password

_REG_RESULT_KEY = "asusddns_reg_result"


def _poster(service: str = "restart_ddns") -> AsyncMock:
    """Build a push callback that reports the given service ran."""

    return AsyncMock(return_value={"run_service": service})


def _data(current: dict[ARDdnsField, Any] | None) -> AsyncMock:
    """Build a get-data callback for the given current DDNS data."""

    return AsyncMock(return_value={ARDdnsSourceUniversal: current})


def _payload(callback: AsyncMock) -> dict[str, Any]:
    """Decode the pushed request body."""

    request = callback.await_args.kwargs["request"]
    assert callback.await_args.kwargs["endpoint"] is AREndpoint.PUSH_DATA
    return json.loads(request)


def _deregister_callback(
    poll_results: list[Any],
    *,
    dispatch: Any = "",
    clean: Any = "",
) -> AsyncMock:
    """Build a callback serving the deregistration endpoints."""

    polls = iter(poll_results)

    async def serve(**kwargs: Any) -> Any:
        endpoint = kwargs["endpoint"]
        if endpoint is AREndpoint.DDNS_UNREGISTER:
            return dispatch
        if endpoint is AREndpoint.DDNS_CLEAN:
            return clean
        entry = next(polls)
        return {_REG_RESULT_KEY: entry} if isinstance(entry, str) else entry

    return AsyncMock(side_effect=serve)


@pytest.fixture(autouse=True)
def _fast_poll(monkeypatch: pytest.MonkeyPatch) -> None:
    """Poll without sleeping."""

    monkeypatch.setattr(action_module, "_POLL_INTERVAL", 0)


class TestState:
    """Master toggle command."""

    @pytest.mark.parametrize(("state", "expected"), [(True, 1), (False, 0)])
    async def test_toggle(self, state: bool, expected: int) -> None:
        """A STATE command sets ddns_enable_x and restarts DDNS."""

        callback = _poster()
        action = ARDdnsAction(command=ARDdnsCommand.STATE, state=state)
        result = await run_action(callback, action)

        assert result.success is True
        payload = _payload(callback)
        assert payload["action_mode"] == "apply"
        assert payload["rc_service"] == "restart_ddns"
        assert payload["ddns_enable_x"] == expected

    async def test_no_state(self) -> None:
        """A STATE command without a state is rejected."""

        callback = _poster()
        action = ARDdnsAction(command=ARDdnsCommand.STATE)
        result = await run_action(callback, action)

        assert result.success is False
        callback.assert_not_awaited()


class TestSet:
    """Config write command."""

    async def test_full_config(self) -> None:
        """A SET command writes every given field."""

        callback = _poster()
        action = ARDdnsAction(
            command=ARDdnsCommand.SET,
            state=True,
            config={
                ARDdnsField.SERVER: ARDdnsServer.DYNDNS,
                ARDdnsField.HOSTNAME: Hostname("myhost.dyndns.org"),
                ARDdnsField.USERNAME: "user",
                ARDdnsField.PASSWORD: Password("secret"),
                ARDdnsField.IPV6_UPDATE: True,
                ARDdnsField.WILDCARD: False,
                ARDdnsField.VERIFICATION: True,
                ARDdnsField.VERIFICATION_PERIOD: 60,
                ARDdnsField.REFRESH_INTERVAL: 21,
                ARDdnsField.WAN_UNIT: -1,
            },
        )
        result = await run_action(callback, action)

        assert result.success is True
        payload = _payload(callback)
        assert payload["rc_service"] == "restart_ddns"
        assert payload["ddns_enable_x"] == 1
        assert payload["ddns_server_x"] == "WWW.DYNDNS.ORG"
        assert payload["ddns_hostname_x"] == "myhost.dyndns.org"
        assert payload["ddns_username_x"] == "user"
        assert payload["ddns_passwd_x"] == "secret"
        assert payload["ddns_ipv6_update"] == 1
        assert payload["ddns_wildcard_x"] == 0
        assert payload["ddns_regular_check"] == 1
        assert payload["ddns_regular_period"] == 60
        assert payload["ddns_refresh_x"] == 21
        assert payload["ddns_wan_unit"] == -1

    async def test_empty(self) -> None:
        """A SET command with nothing to write is rejected."""

        callback = _poster()
        action = ARDdnsAction(command=ARDdnsCommand.SET)
        result = await run_action(callback, action)

        assert result.success is False
        callback.assert_not_awaited()

    async def test_none_clears(self) -> None:
        """A None value writes an empty setting."""

        callback = _poster()
        action = ARDdnsAction(
            command=ARDdnsCommand.SET,
            config={ARDdnsField.USERNAME: None},
        )
        result = await run_action(callback, action)

        assert result.success is True
        assert _payload(callback)["ddns_username_x"] == ""

    @pytest.mark.parametrize(
        "config",
        [
            {ARDdnsField.SERVER: "NOT.A.SERVER"},
            {ARDdnsField.IPV6_UPDATE: "maybe"},
            {ARDdnsField.VERIFICATION_PERIOD: "soon"},
        ],
    )
    async def test_bad_value(self, config: dict[ARDdnsField, Any]) -> None:
        """A bad value rejects the whole write."""

        callback = _poster()
        action = ARDdnsAction(command=ARDdnsCommand.SET, config=config)
        result = await run_action(callback, action)

        assert result.success is False
        callback.assert_not_awaited()

    async def test_hostname_change_unbinds(self) -> None:
        """A hostname change resets the replace status."""

        callback = _poster()
        get_data = _data({ARDdnsField.HOSTNAME: Hostname("old.example.com")})
        action = ARDdnsAction(
            command=ARDdnsCommand.SET,
            config={ARDdnsField.HOSTNAME: "new.example.com"},
        )
        await run_action(callback, action, get_data_callback=get_data)

        assert _payload(callback)["ddns_replace_status"] == 0

    async def test_hostname_unchanged(self) -> None:
        """An unchanged hostname keeps the replace status."""

        callback = _poster()
        get_data = _data({ARDdnsField.HOSTNAME: Hostname("same.example.com")})
        action = ARDdnsAction(
            command=ARDdnsCommand.SET,
            config={ARDdnsField.HOSTNAME: "same.example.com"},
        )
        await run_action(callback, action, get_data_callback=get_data)

        assert "ddns_replace_status" not in _payload(callback)

    @pytest.mark.parametrize(
        "get_data",
        [None, AsyncMock(return_value=None), _data(None)],
    )
    async def test_hostname_current_unknown(self, get_data: Any) -> None:
        """Without the current config the replace status is left alone."""

        callback = _poster()
        action = ARDdnsAction(
            command=ARDdnsCommand.SET,
            config={ARDdnsField.HOSTNAME: "new.example.com"},
        )
        await run_action(callback, action, get_data_callback=get_data)

        assert "ddns_replace_status" not in _payload(callback)


class TestUpdate:
    """Forced update command."""

    async def test_update(self) -> None:
        """An UPDATE command runs ddnsclient outside the apply flow."""

        callback = _poster("ddnsclient")
        action = ARDdnsAction(command=ARDdnsCommand.UPDATE)
        result = await run_action(callback, action)

        assert result.success is True
        payload = _payload(callback)
        assert payload["action_mode"] == "Update"
        assert payload["rc_service"] == "ddnsclient"


class TestDeregister:
    """Deregistration command."""

    async def test_success(self) -> None:
        """A confirmed deregistration is cleaned up and succeeds."""

        callback = _deregister_callback(["unregister,200"])
        action = ARDdnsAction(command=ARDdnsCommand.DEREGISTER)
        result = await run_action(callback, action)

        assert result.success is True
        endpoints = [
            call.kwargs["endpoint"] for call in callback.await_args_list
        ]
        assert endpoints == [
            AREndpoint.DDNS_UNREGISTER,
            AREndpoint.FETCH_DATA,
            AREndpoint.DDNS_CLEAN,
        ]

    @pytest.mark.parametrize("first", ["register,200", None])
    async def test_polls_until_ready(self, first: Any) -> None:
        """Polling skips stale or broken results until the outcome lands."""

        callback = _deregister_callback([first, "unregister,200"])
        action = ARDdnsAction(command=ARDdnsCommand.DEREGISTER)
        result = await run_action(callback, action)

        assert result.success is True

    async def test_token_bound(self) -> None:
        """A hostname bound to an app account is not released."""

        callback = _deregister_callback(["unregister,200"])
        get_data = _data({ARDdnsField.TOKEN_STATE: True})
        action = ARDdnsAction(command=ARDdnsCommand.DEREGISTER)
        result = await run_action(callback, action, get_data_callback=get_data)

        assert result.success is False
        callback.assert_not_awaited()

    async def test_dispatch_failed(self) -> None:
        """A failed dispatch aborts the deregistration."""

        callback = _deregister_callback(["unregister,200"], dispatch=None)
        action = ARDdnsAction(command=ARDdnsCommand.DEREGISTER)
        result = await run_action(callback, action)

        assert result.success is False

    async def test_poll_timeout(self) -> None:
        """A device that never reports the outcome fails the action."""

        callback = _deregister_callback(["register,200"] * 6)
        action = ARDdnsAction(command=ARDdnsCommand.DEREGISTER)
        result = await run_action(callback, action)

        assert result.success is False

    async def test_rejected_by_server(self) -> None:
        """A non-success outcome fails without a cleanup."""

        callback = _deregister_callback(["unregister,402"])
        action = ARDdnsAction(command=ARDdnsCommand.DEREGISTER)
        result = await run_action(callback, action)

        assert result.success is False
        endpoints = [
            call.kwargs["endpoint"] for call in callback.await_args_list
        ]
        assert AREndpoint.DDNS_CLEAN not in endpoints

    async def test_cleanup_failed(self) -> None:
        """A failed cleanup fails the action."""

        callback = _deregister_callback(["unregister,200"], clean=None)
        action = ARDdnsAction(command=ARDdnsCommand.DEREGISTER)
        result = await run_action(callback, action)

        assert result.success is False

    async def test_dispatch_empty_dict_fails(self) -> None:
        """An async_read {} on a failed dispatch is not read as success."""

        callback = _deregister_callback(["unregister,200"], dispatch={})
        action = ARDdnsAction(command=ARDdnsCommand.DEREGISTER)
        result = await run_action(callback, action)

        assert result.success is False

    async def test_cleanup_empty_dict_fails(self) -> None:
        """An async_read {} on a failed cleanup is not read as success."""

        callback = _deregister_callback(["unregister,200"], clean={})
        action = ARDdnsAction(command=ARDdnsCommand.DEREGISTER)
        result = await run_action(callback, action)

        assert result.success is False


class TestCommon:
    """Cross-command behavior."""

    async def test_unknown_command(self) -> None:
        """An unknown command fails without a push."""

        callback = _poster()
        action = ARDdnsAction(command=ARDdnsCommand.UNKNOWN)
        result = await run_action(callback, action)

        assert result.success is False
        callback.assert_not_awaited()

    async def test_expire_on_success(self) -> None:
        """A successful action expires the DDNS data and its nvram items."""

        callback = _poster()
        expire = AsyncMock()
        action = ARDdnsAction(command=ARDdnsCommand.STATE, state=True)
        await run_action(callback, action, expire_callback=expire)

        expire.assert_any_await(ARDdnsSourceUniversal)
        for item in DDNS_REQUEST:
            expire.assert_any_await(item)
        assert expire.await_count == 1 + len(DDNS_REQUEST)

    async def test_no_expire_on_failure(self) -> None:
        """A failed action leaves the cached DDNS data alone."""

        callback = AsyncMock(return_value=None)
        expire = AsyncMock()
        action = ARDdnsAction(command=ARDdnsCommand.STATE, state=True)
        result = await run_action(callback, action, expire_callback=expire)

        assert result.success is False
        expire.assert_not_awaited()

    async def test_raw_callback_preferred(self) -> None:
        """The raw callback posts the request when given."""

        callback = AsyncMock()
        raw = _poster()
        action = ARDdnsAction(command=ARDdnsCommand.STATE, state=True)
        result = await run_action(callback, action, raw_callback=raw)

        assert result.success is True
        callback.assert_not_awaited()
        _payload(raw)

    async def test_update_ignores_config(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """State and config on UPDATE are ignored with a debug note."""

        callback = _poster("ddnsclient")
        action = ARDdnsAction(
            command=ARDdnsCommand.UPDATE,
            state=True,
            config={ARDdnsField.HOSTNAME: Hostname("host")},
        )
        with caplog.at_level("DEBUG"):
            result = await run_action(callback, action)

        assert result.success is True
        assert "ignores state and config" in caplog.text

    async def test_set_logs_non_writable_field(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A SET config field with no nvram key is logged as dropped."""

        callback = _poster()
        action = ARDdnsAction(
            command=ARDdnsCommand.SET,
            config={
                ARDdnsField.HOSTNAME: Hostname("host"),
                ARDdnsField.STATUS: "200",
            },
        )
        with caplog.at_level("DEBUG"):
            result = await run_action(callback, action)

        assert result.success is True
        assert "non-writable config fields" in caplog.text


class TestEquality:
    """Action identity."""

    def test_key_distinguishes_config(self) -> None:
        """Actions differ by command, state and config."""

        base = ARDdnsAction(command=ARDdnsCommand.SET, state=True)
        same = ARDdnsAction(command=ARDdnsCommand.SET, state=True)
        assert base == same
        assert hash(base) == hash(same)

        other = ARDdnsAction(
            command=ARDdnsCommand.SET,
            state=True,
            config={ARDdnsField.HOSTNAME: Hostname("host")},
        )
        assert base != other
        assert hash(base) != hash(other)
