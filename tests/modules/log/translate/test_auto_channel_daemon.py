"""Tests for the auto channel selection daemon event translation."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.log.enums import AREventKey
from asusrouter.modules.log.translate.auto_channel_daemon import (
    PATTERNS,
    AREventAutoChannelDaemon,
)
from asusrouter.modules.wifi import ARWiFiBandwidth, ARWiFiFrequency
from asusrouter.tools.identifiers import WiFiInterface
from tests.modules.log.translate import unread

_KEY = AREventKey


def _translate(content: str) -> dict[AREventKey, Any]:
    """Translate a raw acsd message."""

    return PATTERNS.translate(content)


class TestChannelSpec:
    """Messages naming the channel the daemon settled on."""

    @pytest.mark.parametrize(
        ("content", "event"),
        [
            (
                "wl1.1: Adjusted channel spec: 0xe832 (36/160)",
                AREventAutoChannelDaemon.CHANNEL_ADJUSTED,
            ),
            (
                "wl1.1: selected channel spec: 0xe832 (36/160)",
                AREventAutoChannelDaemon.CHANNEL_SELECTED,
            ),
            (
                "wl1.1: NONACSD channel switching to channel spec: "
                "0xe832 (36/160)",
                AREventAutoChannelDaemon.CHANNEL_SWITCHED,
            ),
        ],
    )
    def test_verbs(self, content: str, event: str) -> None:
        """Each wording is its own event, named after the verb used."""

        assert _translate(content) == {
            _KEY.EVENT_TYPE: event,
            _KEY.RAW: content,
            _KEY.WL_ID: WiFiInterface(1, 1),
            _KEY.CHANNEL: 36,
            _KEY.BANDWIDTH: ARWiFiBandwidth.WIDTH_160,
        }

    def test_ethernet_named_radio(self) -> None:
        """A radio named `ethN` is an interface, never a wl unit."""

        content = "eth7: selected channel spec: 0xe06a (100/80)"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventAutoChannelDaemon.CHANNEL_SELECTED,
            _KEY.RAW: content,
            _KEY.INTERFACE: "eth7",
            _KEY.CHANNEL: 100,
            _KEY.BANDWIDTH: ARWiFiBandwidth.WIDTH_80,
        }

    @pytest.mark.parametrize(
        "spec", ["0x1007 (7)", "0x180a (8l)", "0x1904 (6u)"]
    )
    def test_width_left_out(self, spec: str) -> None:
        """A spec naming a sideband instead of a width reports no width."""

        event = _translate(f"wl0.1: selected channel spec: {spec}")

        assert _KEY.CHANNEL in event
        assert _KEY.BANDWIDTH not in event

    def test_unknown_width_dropped(self) -> None:
        """A width the enum does not know is left out, not reported."""

        content = "wl0.1: selected channel spec: 0x1007 (7/33)"

        assert _KEY.BANDWIDTH not in _translate(content)


class TestPolicy:
    """Messages naming the policy the daemon runs."""

    def test_policy_selected(self) -> None:
        """The frequency band is read as the typed frequency."""

        content = "wl0.1: Selecting 2g band ACS policy"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventAutoChannelDaemon.POLICY_SELECTED,
            _KEY.RAW: content,
            _KEY.WL_ID: WiFiInterface(0, 1),
            _KEY.FREQUENCY: ARWiFiFrequency.FREQ_2G,
        }

    def test_five_gigahertz(self) -> None:
        """The other observed band resolves as well."""

        content = "eth7: Selecting 5g band ACS policy"
        event = _translate(content)

        assert event[_KEY.FREQUENCY] is ARWiFiFrequency.FREQ_5G
        assert event[_KEY.INTERFACE] == "eth7"

    def test_unknown_frequency_dropped(self) -> None:
        """A band the enum does not know is left out, not reported."""

        content = "wl0.1: Selecting 9g band ACS policy"

        assert _KEY.FREQUENCY not in _translate(content)


class TestUnhandled:
    """Messages deliberately left untranslated."""

    @pytest.mark.parametrize(
        "content",
        [
            # Numeric driver codes with no confirmed meaning
            "acs_update_driver(441): acs update failed ret code: -22",
            "acs_set_chspec: 0xe832 (36/160) for reason ACS_INIT",
            "acs_init_run(1000): wl0.1: update driver failed",
        ],
    )
    def test_internal_traces(self, content: str) -> None:
        """A driver trace stays unknown rather than being guessed at."""

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventAutoChannelDaemon.UNKNOWN,
            _KEY.RAW: unread(content),
        }
