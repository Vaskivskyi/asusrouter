"""Tests for the service action module."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from asusrouter.const import AR_CALL_RUN_ACTION
from asusrouter.modules.common.command import ARService
from asusrouter.modules.common.status import MODIFY_KEY
from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.service.action import (
    ARServiceAction,
    ARServiceResult,
    _as_list,
    _triggers_reboot,
    build_service_request,
    read_service_result,
    run_action,
)
from asusrouter.registry import ARCallableRegistry as ARCallReg


class TestAsList:
    """Tests for _as_list coercion."""

    @pytest.mark.parametrize(
        ("services", "expected"),
        [
            (ARService.WIRELESS_RESTART, [ARService.WIRELESS_RESTART]),
            ("restart_sdn 3", ["restart_sdn 3"]),
            (
                [ARService.WIRELESS_RESTART, "restart_sdn 3"],
                [ARService.WIRELESS_RESTART, "restart_sdn 3"],
            ),
        ],
    )
    def test_as_list(self, services: Any, expected: list[Any]) -> None:
        """A single service or an iterable both yield a list."""

        assert _as_list(services) == expected


class TestBuildServiceRequest:
    """Tests for build_service_request."""

    def test_single_service(self) -> None:
        """A single service yields an apply body with one rc_service."""

        assert build_service_request(ARService.WIRELESS_RESTART) == (
            '{"action_mode":"apply","rc_service":"restart_wireless"}'
        )

    def test_multiple_services(self) -> None:
        """Multiple services join with a semicolon; inline args kept."""

        request = build_service_request(
            [ARService.WIRELESS_RESTART, "restart_sdn 3"]
        )
        assert request == (
            '{"action_mode":"apply",'
            '"rc_service":"restart_wireless;restart_sdn 3"}'
        )

    def test_with_arguments(self) -> None:
        """Extra arguments are folded into the body."""

        request = build_service_request(
            ARService.WIRELESS_RESTART, arguments={"wl0_radio": "0"}
        )
        assert request == (
            '{"action_mode":"apply",'
            '"rc_service":"restart_wireless","wl0_radio":"0"}'
        )


class TestReadServiceResult:
    """Tests for read_service_result."""

    def test_echo_matches_requested(self) -> None:
        """A run_service echo equal to the request is a success."""

        result = read_service_result(
            {"run_service": "restart_wireless"},
            ARService.WIRELESS_RESTART,
        )
        assert result == ARServiceResult(success=True)

    def test_echo_matches_ignoring_trailing_semicolon(self) -> None:
        """Trailing semicolons on either side are ignored."""

        result = read_service_result(
            {"run_service": "restart_wireless;restart_sdn 3;"},
            [ARService.WIRELESS_RESTART, "restart_sdn 3"],
        )
        assert result.success is True

    def test_echo_mismatch(self) -> None:
        """A run_service echo unequal to the request is a failure."""

        result = read_service_result(
            {"run_service": "restart_wireless"},
            [ARService.WIRELESS_RESTART, "restart_sdn 3"],
        )
        assert result.success is False

    def test_echo_without_services(self) -> None:
        """A non-empty echo with no expected services is a success."""

        assert (
            read_service_result({"run_service": "restart_wireless"}).success
            is True
        )

    def test_empty_echo_without_services(self) -> None:
        """An empty echo with no expected services is a failure."""

        assert read_service_result({"run_service": ""}).success is False

    def test_modify_fallback(self) -> None:
        """With no echo, a truthy modify flag is a success."""

        assert read_service_result({MODIFY_KEY: "1"}).success is True
        assert read_service_result({MODIFY_KEY: "0"}).success is False

    def test_needed_time_and_id(self) -> None:
        """restart_needed_time and id are parsed into the result."""

        result = read_service_result(
            {
                "run_service": "restart_wireless",
                "restart_needed_time": "8",
                "id": "2",
            },
            ARService.WIRELESS_RESTART,
        )
        assert result == ARServiceResult(
            success=True, needed_time=8, last_id=2
        )

    def test_needed_time_defaults_when_id_present(self) -> None:
        """An id with no restart_needed_time falls back to the default."""

        result = read_service_result(
            {"run_service": "restart_wireless", "id": "7"},
            ARService.WIRELESS_RESTART,
        )
        assert result.needed_time == 5
        assert result.last_id == 7

    def test_no_id_no_time(self) -> None:
        """No id and no restart_needed_time leaves both unset."""

        result = read_service_result(
            {"run_service": "restart_wireless"},
            ARService.WIRELESS_RESTART,
        )
        assert result.needed_time is None
        assert result.last_id is None

    def test_none_response(self) -> None:
        """A None response (no 200 reached) is a failure."""

        assert read_service_result(None).success is False

    def test_plain_text_body_is_dispatched(self) -> None:
        """A non-JSON 200 body (e.g. NOT MODIFIED) is a success."""

        result = read_service_result("NOT MODIFIED", ARService.DNS_RESTART)
        assert result == ARServiceResult(success=True)

    def test_empty_text_body(self) -> None:
        """An empty body carries no evidence of dispatch."""

        assert read_service_result("").success is False
        assert read_service_result("   ").success is False

    def test_json_string_body(self) -> None:
        """A JSON string body is parsed and its echo checked."""

        result = read_service_result(
            '{"run_service":"restart_wireless"}',
            ARService.WIRELESS_RESTART,
        )
        assert result.success is True

    def test_empty_json_dict_is_dispatched(self) -> None:
        """An empty JSON 200 body counts as dispatched."""

        assert read_service_result({}, ARService.DNS_RESTART).success is True


class TestARServiceAction:
    """Tests for ARServiceAction."""

    def test_single_service(self) -> None:
        """A single service is stored as a one-item list."""

        action = ARServiceAction(ARService.WIRELESS_RESTART)
        assert action.services == [ARService.WIRELESS_RESTART]
        assert action.arguments == {}

    def test_services_and_arguments(self) -> None:
        """Services and arguments are stored as given."""

        action = ARServiceAction(
            [ARService.WIRELESS_RESTART, "restart_sdn 3"],
            arguments={"wl0_radio": "0"},
        )
        assert action.services == [
            ARService.WIRELESS_RESTART,
            "restart_sdn 3",
        ]
        assert action.arguments == {"wl0_radio": "0"}

    def test_registered(self) -> None:
        """The action resolves a run_action callable via the registry."""

        assert (
            ARCallReg.get_callable(
                ARServiceAction(ARService.WIRELESS_RESTART),
                AR_CALL_RUN_ACTION,
            )
            is run_action
        )


class TestRunAction:
    """Tests for run_action."""

    async def test_success_via_raw_callback(self) -> None:
        """A run posts to PUSH_DATA via the raw callback; text = success."""

        raw_callback = AsyncMock(return_value="NOT MODIFIED")
        callback = AsyncMock()
        action = ARServiceAction(
            ARService.WIRELESS_RESTART, arguments={"wl0_radio": "0"}
        )

        result = await run_action(callback, action, raw_callback=raw_callback)

        assert result.success is True
        callback.assert_not_awaited()
        call = raw_callback.await_args.kwargs
        assert call["endpoint"] == AREndpoint.PUSH_DATA
        assert '"rc_service":"restart_wireless"' in call["request"]
        assert '"wl0_radio":"0"' in call["request"]

    async def test_falls_back_to_callback(self) -> None:
        """With no raw callback, the plain callback posts the request."""

        callback = AsyncMock(return_value={"run_service": "restart_wireless"})
        action = ARServiceAction(ARService.WIRELESS_RESTART)

        result = await run_action(callback, action)

        assert result.success is True
        assert callback.await_args.kwargs["endpoint"] == AREndpoint.PUSH_DATA

    async def test_no_services(self) -> None:
        """An action with no services fails without a call."""

        callback = AsyncMock()
        raw_callback = AsyncMock()
        result = await run_action(
            callback, ARServiceAction([]), raw_callback=raw_callback
        )

        assert result.success is False
        callback.assert_not_awaited()
        raw_callback.assert_not_awaited()

    async def test_reboot_marks_identity(self) -> None:
        """A successful reboot flags the identity for reconnect."""

        raw_callback = AsyncMock(return_value="NOT MODIFIED")
        identity = Mock()
        action = ARServiceAction(ARService.REBOOT)

        await run_action(
            AsyncMock(), action, raw_callback=raw_callback, identity=identity
        )

        identity.mark_reboot.assert_called_once_with()

    async def test_reboot_failure_does_not_mark(self) -> None:
        """A failed reboot leaves the identity untouched."""

        raw_callback = AsyncMock(return_value="")
        identity = Mock()

        await run_action(
            AsyncMock(),
            ARServiceAction(ARService.REBOOT),
            raw_callback=raw_callback,
            identity=identity,
        )

        identity.mark_reboot.assert_not_called()

    async def test_non_reboot_does_not_mark(self) -> None:
        """A non-reboot service never flags the identity."""

        raw_callback = AsyncMock(return_value="NOT MODIFIED")
        identity = Mock()

        await run_action(
            AsyncMock(),
            ARServiceAction(ARService.WIRELESS_RESTART),
            raw_callback=raw_callback,
            identity=identity,
        )

        identity.mark_reboot.assert_not_called()

    async def test_reboot_without_identity(self) -> None:
        """A reboot with no identity still succeeds without error."""

        raw_callback = AsyncMock(return_value="NOT MODIFIED")

        result = await run_action(
            AsyncMock(),
            ARServiceAction(ARService.REBOOT),
            raw_callback=raw_callback,
        )

        assert result.success is True


class TestTriggersReboot:
    """Tests for _triggers_reboot."""

    @pytest.mark.parametrize(
        ("services", "expected"),
        [
            ([ARService.REBOOT], True),
            (["reboot"], True),
            ([ARService.WIRELESS_RESTART], False),
            ([ARService.WIRELESS_RESTART, ARService.REBOOT], True),
            ([], False),
        ],
    )
    def test_triggers_reboot(
        self, services: list[Any], expected: bool
    ) -> None:
        """Only a reboot service triggers a reboot."""

        assert _triggers_reboot(services) is expected
