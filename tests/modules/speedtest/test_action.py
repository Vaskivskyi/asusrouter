"""Tests for the speedtest action."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.speedtest import ARSpeedTestAction, run_action
from asusrouter.registry import ARCallableRegistry as ARCallReg


class TestRunAction:
    """Tests for run_action."""

    async def test_default(self) -> None:
        """A default run stamps the start time, then posts an empty body."""

        callback = AsyncMock()
        result = await run_action(callback, ARSpeedTestAction())
        assert result.success is True

        # First the start time, then the run trigger
        start, run = callback.await_args_list
        assert start.kwargs["endpoint"] == AREndpoint.SET_SPEEDTEST_START_TIME
        assert start.kwargs["request"].startswith("ookla_start_time=")
        assert run.kwargs["endpoint"] == AREndpoint.RUN_SPEEDTEST
        assert run.kwargs["request"] == "type=&id="

    async def test_with_server_and_iface(self) -> None:
        """A targeted run carries the server id and interface."""

        callback = AsyncMock()
        await run_action(
            callback, ARSpeedTestAction(server_id="42", iface="tun11")
        )

        run = callback.await_args_list[1].kwargs
        assert run["request"] == "type=&id=42&iface=tun11"

    async def test_with_integer_server(self) -> None:
        """An integer server id is sent verbatim."""

        callback = AsyncMock()
        await run_action(callback, ARSpeedTestAction(server_id=54112))

        run = callback.await_args_list[1].kwargs
        assert run["request"] == "type=&id=54112"

    async def test_prefers_raw_callback(self) -> None:
        """With a raw callback, both requests post raw and success is True."""

        callback = AsyncMock()
        fetch_raw_callback = AsyncMock(return_value="")

        result = await run_action(
            callback,
            ARSpeedTestAction(),
            fetch_raw_callback=fetch_raw_callback,
        )

        assert result.success is True
        callback.assert_not_awaited()
        assert fetch_raw_callback.await_count == 2

    async def test_failed_run_returns_false(self) -> None:
        """A failed run request reports False."""

        fetch_raw_callback = AsyncMock(return_value=None)

        result = await run_action(
            AsyncMock(),
            ARSpeedTestAction(),
            fetch_raw_callback=fetch_raw_callback,
        )

        assert result.success is False

    def test_registered(self) -> None:
        """The action resolves to the module run_action callable."""

        assert (
            ARCallReg.get_callable(ARSpeedTestAction(), "run_action")
            is run_action
        )


class TestAction:
    """Tests for ARSpeedTestAction."""

    def test_normalizes_integer_id(self) -> None:
        """A positive integer server id is stored as its string form."""

        assert ARSpeedTestAction(54112).server_id == "54112"
        assert ARSpeedTestAction("54112").server_id == "54112"

    def test_default_id_is_none(self) -> None:
        """Without an id the auto server is used."""

        assert ARSpeedTestAction().server_id is None

    @pytest.mark.parametrize("value", [0, -5, "0", "abc", ""])
    def test_non_positive_falls_back_to_auto(self, value: int | str) -> None:
        """Zero, negative, or non-numeric ids fall back to the auto server."""

        assert ARSpeedTestAction(value).server_id is None

    def test_equal_by_server_and_iface(self) -> None:
        """Actions are equal by server id and interface, int or str alike."""

        assert ARSpeedTestAction(54112) == ARSpeedTestAction("54112")
        assert hash(ARSpeedTestAction(1, "tun11")) == hash(
            ARSpeedTestAction(1, "tun11")
        )

    def test_not_equal_on_iface(self) -> None:
        """A differing interface makes actions unequal."""

        assert ARSpeedTestAction(1) != ARSpeedTestAction(1, "tun11")

    def test_not_equal_other_type(self) -> None:
        """Comparison against a non-action is not equal."""

        assert ARSpeedTestAction() != object()
