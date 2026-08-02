"""Auto channel selection daemon (acsd) log event translation."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Any

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.modules.log.enums import AREventKey
from asusrouter.modules.log.translate.common import RADIO_PATTERN
from asusrouter.modules.log.translate.pattern import (
    ARLogPattern,
    ARLogPatternSet,
)
from asusrouter.modules.wifi import ARWiFiBandwidth, ARWiFiFrequency
from asusrouter.tools.enum import FromStrMixin
from asusrouter.tools.identifiers import WiFiInterface

if TYPE_CHECKING:
    from collections.abc import Callable

# The chanspec the daemon settled on, as raw hex then `<channel>[/<width>]`
# TODO: a 40 MHz spec names its sideband instead of a width (`8l`, `6u`
# against `36/160`), so those events report no bandwidth - add it
_CHANSPEC = r"channel spec: \S+ \((?P<channel>\d+)(?:/(?P<bandwidth>\d+))?"


class AREventAutoChannelDaemon(FromStrMixin, StrEnum):
    """Auto channel selection daemon event types."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    CHANNEL_ADJUSTED = "channel_adjusted"
    CHANNEL_SELECTED = "channel_selected"
    CHANNEL_SWITCHED = "channel_switched"
    POLICY_SELECTED = "policy_selected"


def _bandwidth(value: str) -> ARWiFiBandwidth | None:
    """Read a channel width, dropping one the enum does not know."""

    bandwidth = ARWiFiBandwidth.from_value(value)

    return bandwidth if bandwidth is not ARWiFiBandwidth.UNKNOWN else None


def _frequency(value: str) -> ARWiFiFrequency | None:
    """Read a frequency band, dropping one the enum does not know."""

    frequency = ARWiFiFrequency.from_value(value)

    return frequency if frequency is not ARWiFiFrequency.UNKNOWN else None


_CONVERT: dict[AREventKey, Callable[[str], Any]] = {
    AREventKey.BANDWIDTH: _bandwidth,
    AREventKey.CHANNEL: int,
    AREventKey.WL_ID: WiFiInterface.from_value_safe,
}


PATTERNS = ARLogPatternSet(
    AREventAutoChannelDaemon.UNKNOWN,
    (
        ARLogPattern(
            AREventAutoChannelDaemon.CHANNEL_ADJUSTED,
            rf"{RADIO_PATTERN}: Adjusted {_CHANSPEC}",
            convert=_CONVERT,
            marker="Adjusted channel spec",
        ),
        ARLogPattern(
            AREventAutoChannelDaemon.CHANNEL_SELECTED,
            rf"{RADIO_PATTERN}: selected {_CHANSPEC}",
            convert=_CONVERT,
            marker="selected channel spec",
        ),
        ARLogPattern(
            AREventAutoChannelDaemon.CHANNEL_SWITCHED,
            rf"{RADIO_PATTERN}: NONACSD channel switching to {_CHANSPEC}",
            convert=_CONVERT,
            marker="channel switching to",
        ),
        ARLogPattern(
            AREventAutoChannelDaemon.POLICY_SELECTED,
            rf"{RADIO_PATTERN}: Selecting (?P<frequency>\d+g\d*) band",
            convert={
                AREventKey.FREQUENCY: _frequency,
                AREventKey.WL_ID: WiFiInterface.from_value_safe,
            },
            marker="band ACS policy",
        ),
    ),
)
