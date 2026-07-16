"""Tests for the appGet hooks."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.endpoint.hooks import ARHook, hook_request, hook_value


class _FakeItem:
    """A minimal ARHookItem implementation for tests."""

    def as_hook(self) -> tuple[ARHook, str]:
        """Render as an `nvram_get` hook call."""

        return (ARHook.NVRAM_GET, "some_key")


class TestARHook:
    """Tests for the ARHook enum."""

    @pytest.mark.parametrize(
        ("member", "value"),
        [
            (ARHook.UPTIME, "uptime"),
            (ARHook.NETDEV, "netdev"),
            (ARHook.UI_SUPPORT, "get_ui_support"),
            (ARHook.CHANNEL_LIST_5G2, "channel_list_5g_2"),
        ],
    )
    def test_values(self, member: ARHook, value: str) -> None:
        """Each member maps to its hook function name."""

        assert member.value == value

    def test_from_value_unknown(self) -> None:
        """Unknown hooks resolve to UNKNOWN."""

        assert ARHook.from_value("nope") is ARHook.UNKNOWN


class TestHookRequest:
    """Tests for hook_request."""

    @pytest.mark.parametrize(
        ("hooks", "expected"),
        [
            ((ARHook.UPTIME,), "hook=uptime()"),
            (((ARHook.NETDEV, "appobj"),), "hook=netdev(appobj)"),
            (
                (ARHook.UPTIME, (ARHook.NETDEV, "appobj")),
                "hook=uptime();netdev(appobj)",
            ),
            ((_FakeItem(),), "hook=nvram_get(some_key)"),
            (
                (ARHook.UPTIME, _FakeItem()),
                "hook=uptime();nvram_get(some_key)",
            ),
        ],
        ids=["single", "with_args", "multiple", "item", "mixed"],
    )
    def test_build(self, hooks: Any, expected: str) -> None:
        """Requests join `name(args)` parts under a single `hook=`."""

        assert hook_request(*hooks) == expected


class TestHookValue:
    """Tests for hook_value."""

    def test_non_dict_returns_none(self) -> None:
        """A non-dict response yields None."""

        assert hook_value(None, ARHook.UPTIME) is None

    def test_plain_hook_keyed_by_value(self) -> None:
        """Plain hooks read the response by their name."""

        assert hook_value({"uptime": 42}, ARHook.UPTIME) == 42
        assert hook_value({}, ARHook.UPTIME) is None

    def test_item_keyed_by_argument(self) -> None:
        """Argument-carrying items read the response by their argument."""

        assert hook_value({"some_key": "v"}, _FakeItem()) == "v"
        assert hook_value({}, _FakeItem()) is None
