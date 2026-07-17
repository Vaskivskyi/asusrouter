"""Tests for the parental control data source."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from asusrouter.modules.nvram import ARNvramType
from asusrouter.modules.parental_control.enums import (
    ARParentalControlField,
    ARParentalControlScheduleMode,
    ARParentalControlType,
)
from asusrouter.modules.parental_control.schedule.source import (
    DEFAULT_TIMEMAP,
    ARParentalControlSourceUniversal,
    fetch_state,
    rule_entry_count,
    rule_schedule_mode,
    serialize_rules,
    translate_state,
)
from asusrouter.modules.parental_control.schedule.timemap import (
    WEEKDAYS,
    WEEKEND,
    ARScheduleEntry,
)
from asusrouter.tools.identifiers import MacAddress

_F = ARParentalControlField
_T = ARParentalControlType
_M = ARParentalControlScheduleMode

# Two aligned rules across the parallel `>`-joined lists
_MAC = "AA:BB:CC:DD:EE:FF&#6211:22:33:44:55:66"
_NAME = "phone&#62tablet"
_TYPE = "2&#621"
_TIMEMAP = "W03E21000700&#60W04122000800&#62W01E21000700"


class TestGetState:
    """Tests for fetch_state."""

    async def test_fetches_via_nvram(self) -> None:
        """The parental control items are requested from the NVRAM module."""

        values = {ARNvramType.PARENTAL_CONTROL_STATE: "1"}
        get_data = AsyncMock(return_value=values)
        callback = AsyncMock()

        result = await fetch_state(
            callback,
            ARParentalControlSourceUniversal,
            get_data_callback=get_data,
        )

        assert result == values
        callback.assert_not_awaited()
        assert get_data.await_args.args[0] == (
            ARNvramType.PARENTAL_CONTROL_STATE,
            ARNvramType.PARENTAL_CONTROL_MAC,
            ARNvramType.PARENTAL_CONTROL_NAME,
            ARNvramType.PARENTAL_CONTROL_TYPE,
            ARNvramType.PARENTAL_CONTROL_TIMEMAP,
        )

    async def test_no_get_data_callback(self) -> None:
        """Without a data callback nothing is fetched."""

        callback = AsyncMock()
        result = await fetch_state(callback, ARParentalControlSourceUniversal)
        assert result == {}
        callback.assert_not_awaited()

    async def test_non_dict_response(self) -> None:
        """A non-dict response is normalized to an empty dict."""

        get_data = AsyncMock(return_value=None)
        result = await fetch_state(
            AsyncMock(),
            ARParentalControlSourceUniversal,
            get_data_callback=get_data,
        )
        assert result == {}


class TestTranslateState:
    """Tests for translate_state."""

    @pytest.mark.parametrize("data", [None, {}, "text", []])
    def test_empty(self, data: Any) -> None:
        """Non-dict or empty data yields an empty result."""

        assert translate_state(data) == {}

    @pytest.mark.parametrize(
        ("state", "expected"),
        [("1", True), ("0", False), (None, False)],
    )
    def test_state(self, state: Any, expected: bool) -> None:
        """The rules-engine master state reflects MULTIFILTER_ALL."""

        result = translate_state({"MULTIFILTER_ALL": state})
        assert result[_F.STATE] is expected
        assert result[_F.RULES] == []

    def test_rules_aligned(self) -> None:
        """Parallel lists decode into aligned, typed rule dicts."""

        result = translate_state(
            {
                "MULTIFILTER_ALL": "1",
                "MULTIFILTER_MAC": _MAC,
                "MULTIFILTER_DEVICENAME": _NAME,
                "MULTIFILTER_ENABLE": _TYPE,
                "MULTIFILTER_MACFILTER_DAYTIME_V2": _TIMEMAP,
            }
        )
        first, second = result[_F.RULES]

        assert isinstance(first[_F.MAC], MacAddress)
        assert first[_F.MAC].as_asus() == "AA:BB:CC:DD:EE:FF"
        assert first[_F.NAME] == "phone"
        assert first[_F.TYPE] is _T.BLOCK
        assert first[_F.MODE] is _M.OFFLINE
        assert first[_F.TIMEMAP] == "W03E21000700<W04122000800"

        assert second[_F.NAME] == "tablet"
        assert second[_F.TYPE] is _T.TIME
        assert second[_F.MODE] is _M.OFFLINE
        assert second[_F.TIMEMAP] == "W01E21000700"

    def test_empty_mac_row_skipped(self) -> None:
        """A row with an empty MAC contributes no rule."""

        result = translate_state(
            {
                "MULTIFILTER_MAC": "&#62AA:BB:CC:DD:EE:FF",
                "MULTIFILTER_DEVICENAME": "&#62kept",
                "MULTIFILTER_ENABLE": "2&#622",
            }
        )
        [rule] = result[_F.RULES]
        assert rule[_F.NAME] == "kept"

    def test_unparseable_mac_kept_raw(self) -> None:
        """An unparseable MAC is kept verbatim so nothing is lost."""

        result = translate_state({"MULTIFILTER_MAC": "not-a-mac"})
        [rule] = result[_F.RULES]
        assert rule[_F.MAC] == "not-a-mac"

    def test_ragged_lists_padded(self) -> None:
        """Missing name/type/timemap fields default without raising."""

        result = translate_state({"MULTIFILTER_MAC": "AA:BB:CC:DD:EE:FF"})
        [rule] = result[_F.RULES]
        assert rule[_F.NAME] == ""
        assert rule[_F.TYPE] is _T.UNKNOWN
        assert rule[_F.MODE] is _M.UNKNOWN
        assert rule[_F.TIMEMAP] == ""


class TestSerializeRules:
    """Tests for serialize_rules."""

    def test_empty(self) -> None:
        """An empty list serializes to four empty lists."""

        assert serialize_rules([]) == {
            "MULTIFILTER_MAC": "",
            "MULTIFILTER_DEVICENAME": "",
            "MULTIFILTER_ENABLE": "",
            "MULTIFILTER_MACFILTER_DAYTIME_V2": "",
        }

    def test_mac_uppercased(self) -> None:
        """A MacAddress serializes in the device's uppercase ASUS format."""

        rule = {
            _F.MAC: MacAddress.from_value("aa:bb:cc:dd:ee:ff"),
            _F.NAME: "pc",
            _F.TYPE: _T.BLOCK,
            _F.TIMEMAP: "W01E21000700",
        }
        assert serialize_rules([rule]) == {
            "MULTIFILTER_MAC": "AA:BB:CC:DD:EE:FF",
            "MULTIFILTER_DEVICENAME": "pc",
            "MULTIFILTER_ENABLE": "2",
            "MULTIFILTER_MACFILTER_DAYTIME_V2": "W01E21000700",
        }

    def test_defaults(self) -> None:
        """A raw-string MAC passes through; blank timemap uses the default."""

        rule = {_F.MAC: "AA:BB:CC:DD:EE:FF", _F.TYPE: _T.TIME}
        result = serialize_rules([rule])
        assert result["MULTIFILTER_MAC"] == "AA:BB:CC:DD:EE:FF"
        assert result["MULTIFILTER_DEVICENAME"] == ""
        assert result["MULTIFILTER_MACFILTER_DAYTIME_V2"] == DEFAULT_TIMEMAP

    def test_round_trip(self) -> None:
        """Parsing then serializing reproduces the decoded lists."""

        rules = translate_state(
            {
                "MULTIFILTER_MAC": _MAC,
                "MULTIFILTER_DEVICENAME": _NAME,
                "MULTIFILTER_ENABLE": _TYPE,
                "MULTIFILTER_MACFILTER_DAYTIME_V2": _TIMEMAP,
            }
        )[_F.RULES]

        assert serialize_rules(rules) == {
            "MULTIFILTER_MAC": "AA:BB:CC:DD:EE:FF>11:22:33:44:55:66",
            "MULTIFILTER_DEVICENAME": "phone>tablet",
            "MULTIFILTER_ENABLE": "2>1",
            "MULTIFILTER_MACFILTER_DAYTIME_V2": (
                "W03E21000700<W04122000800>W01E21000700"
            ),
        }


class TestScheduleMode:
    """Online/offline schedule mode handling."""

    def test_parse_online(self) -> None:
        """An M-prefixed timemap parses as the online mode."""

        result = translate_state(
            {
                "MULTIFILTER_MAC": "AA:BB:CC:DD:EE:FF",
                "MULTIFILTER_ENABLE": "1",
                "MULTIFILTER_MACFILTER_DAYTIME_V2": "M13E17002100",
            }
        )
        [rule] = result[_F.RULES]
        assert rule[_F.MODE] is _M.ONLINE

    def test_serialize_mode_field_rewrites_timemap(self) -> None:
        """An explicit MODE field flips the timemap entry prefixes."""

        rule = {
            _F.MAC: "AA:BB:CC:DD:EE:FF",
            _F.TYPE: _T.TIME,
            _F.MODE: _M.ONLINE,
            _F.TIMEMAP: "W03E21000700<W04122000800",
        }
        result = serialize_rules([rule])
        assert result["MULTIFILTER_MACFILTER_DAYTIME_V2"] == (
            "M03E21000700<M04122000800"
        )

    def test_serialize_unknown_mode_keeps_timemap(self) -> None:
        """An UNKNOWN MODE field leaves the timemap untouched."""

        rule = {
            _F.MAC: "AA:BB:CC:DD:EE:FF",
            _F.TYPE: _T.TIME,
            _F.MODE: _M.UNKNOWN,
            _F.TIMEMAP: "W01E21000700",
        }
        result = serialize_rules([rule])
        assert result["MULTIFILTER_MACFILTER_DAYTIME_V2"] == "W01E21000700"

    def test_rule_schedule_mode_field_wins(self) -> None:
        """An explicit MODE field overrides the timemap prefix."""

        rule = {_F.MODE: _M.ONLINE, _F.TIMEMAP: "W01E21000700"}
        assert rule_schedule_mode(rule) is _M.ONLINE

    def test_rule_schedule_mode_from_timemap(self) -> None:
        """Without a MODE field the mode comes from the timemap."""

        assert rule_schedule_mode({_F.TIMEMAP: "M01E17002100"}) is _M.ONLINE
        assert rule_schedule_mode({}) is _M.UNKNOWN


class TestScheduleField:
    """The parsed SCHEDULE field and its serialization."""

    def test_parsed_rule_exposes_entries(self) -> None:
        """A parsed rule carries its timemap as schedule entries."""

        result = translate_state(
            {
                "MULTIFILTER_MAC": "AA:BB:CC:DD:EE:FF",
                "MULTIFILTER_ENABLE": "1",
                "MULTIFILTER_MACFILTER_DAYTIME_V2": "W03E21000700",
            }
        )
        [rule] = result[_F.RULES]
        [entry] = rule[_F.SCHEDULE]
        assert entry.days == WEEKDAYS
        assert entry.start_hour == 21

    def test_schedule_wins_over_raw_timemap(self) -> None:
        """A SCHEDULE list is serialized in place of a conflicting raw one."""

        rule = {
            _F.MAC: "AA:BB:CC:DD:EE:FF",
            _F.TYPE: _T.TIME,
            _F.SCHEDULE: [ARScheduleEntry(days=WEEKDAYS, start_hour=8)],
            _F.TIMEMAP: "W04122000800",
        }
        result = serialize_rules([rule])
        assert result["MULTIFILTER_MACFILTER_DAYTIME_V2"] == "W13E08002400"

    def test_schedule_applies_mode(self) -> None:
        """The rule's MODE drives the serialized entry prefixes."""

        rule = {
            _F.MAC: "AA:BB:CC:DD:EE:FF",
            _F.TYPE: _T.TIME,
            _F.MODE: _M.ONLINE,
            _F.SCHEDULE: [ARScheduleEntry(days=WEEKDAYS, start_hour=8)],
        }
        result = serialize_rules([rule])
        assert result["MULTIFILTER_MACFILTER_DAYTIME_V2"] == "M13E08002400"

    def test_entry_count_from_schedule(self) -> None:
        """A SCHEDULE field is counted directly."""

        rule = {
            _F.SCHEDULE: [
                ARScheduleEntry(days=WEEKDAYS),
                ARScheduleEntry(days=WEEKEND),
            ]
        }
        assert rule_entry_count(rule) == 2

    def test_entry_count_from_raw_timemap(self) -> None:
        """Without a SCHEDULE the raw timemap windows are counted."""

        rule = {_F.TIMEMAP: "W03E21000700<W04122000800"}
        assert rule_entry_count(rule) == 2

    def test_entry_count_default(self) -> None:
        """A rule with no schedule counts the seeded default windows."""

        assert rule_entry_count({_F.MAC: "AA:BB:CC:DD:EE:FF"}) == 2
