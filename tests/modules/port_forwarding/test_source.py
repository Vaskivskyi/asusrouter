"""Tests for the port forwarding data source."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.port_forwarding.enums import (
    ARPortForwardingField,
    ARPortForwardingProtocol,
)
from asusrouter.modules.port_forwarding.source import (
    ARPortForwardingSourceUniversal,
    get_state,
    serialize_rules,
    translate_state,
)

# Encoded nvram rule rows: `<name>ext>internal_ip>internal_port>proto>source`
_RULE_TCP = "&#60Web&#6280&#62192.168.1.10&#628080&#62TCP&#62"
_RULE_OTHER = "&#60GRE&#6247&#62192.168.1.20&#62&#62OTHER&#62"
_RULE_SOURCE = "&#60&#62443&#62192.168.1.30&#62&#62UDP&#6210.0.0.0/24"


class TestGetState:
    """Tests for get_state."""

    async def test_fetches_nvram(self) -> None:
        """The port forwarding nvram keys are requested."""

        callback = AsyncMock(return_value={"vts_enable_x": "1"})
        await get_state(callback, ARPortForwardingSourceUniversal)

        request = callback.await_args.kwargs["request"]
        assert callback.await_args.kwargs["endpoint"] is AREndpoint.FETCH_DATA
        assert request.startswith("hook=")
        assert "nvram_get(vts_enable_x)" in request
        assert "nvram_get(vts_rulelist)" in request
        assert "nvram_get(vts1_rulelist)" in request


class TestTranslateState:
    """Tests for translate_state."""

    @pytest.mark.parametrize("data", [None, {}, "text", []])
    def test_empty(self, data: Any) -> None:
        """Non-dict or empty data yields an empty result."""

        assert translate_state(data) == {}

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [("1", True), ("0", False), (None, False)],
    )
    def test_state(self, raw: Any, expected: bool) -> None:
        """The master state reflects vts_enable_x."""

        data = (
            {"vts_enable_x": raw} if raw is not None else {"vts_rulelist": ""}
        )
        result = translate_state(data)
        assert result[ARPortForwardingField.STATE] is expected
        assert result[ARPortForwardingField.RULES] == []

    def test_tcp_rule(self) -> None:
        """A standard TCP rule maps all columns."""

        result = translate_state({"vts_rulelist": _RULE_TCP})
        [rule] = result[ARPortForwardingField.RULES]

        assert rule[ARPortForwardingField.NAME] == "Web"
        assert rule[ARPortForwardingField.PROTOCOL] is (
            ARPortForwardingProtocol.TCP
        )
        assert rule[ARPortForwardingField.EXTERNAL_PORT] == "80"
        assert str(rule[ARPortForwardingField.INTERNAL_IP]) == "192.168.1.10"
        assert rule[ARPortForwardingField.INTERNAL_PORT] == "8080"
        assert rule[ARPortForwardingField.WAN_UNIT] == 0
        assert ARPortForwardingField.SOURCE_IP not in rule
        assert ARPortForwardingField.PROTOCOL_NUMBER not in rule

    def test_other_rule(self) -> None:
        """OTHER carries a protocol number, not an external port."""

        result = translate_state({"vts_rulelist": _RULE_OTHER})
        [rule] = result[ARPortForwardingField.RULES]

        assert rule[ARPortForwardingField.PROTOCOL] is (
            ARPortForwardingProtocol.OTHER
        )
        assert rule[ARPortForwardingField.PROTOCOL_NUMBER] == 47
        assert ARPortForwardingField.EXTERNAL_PORT not in rule
        assert ARPortForwardingField.INTERNAL_PORT not in rule

    def test_other_non_numeric(self) -> None:
        """A non-numeric OTHER protocol slot yields no protocol number."""

        raw = "&#60x&#62abc&#62192.168.1.20&#62&#62OTHER&#62"
        result = translate_state({"vts_rulelist": raw})
        [rule] = result[ARPortForwardingField.RULES]
        assert ARPortForwardingField.PROTOCOL_NUMBER not in rule

    def test_source_ip(self) -> None:
        """A source restriction parses to an interface; blank name drops."""

        result = translate_state({"vts_rulelist": _RULE_SOURCE})
        [rule] = result[ARPortForwardingField.RULES]

        assert str(rule[ARPortForwardingField.SOURCE_IP]) == "10.0.0.0/24"
        assert ARPortForwardingField.NAME not in rule
        assert ARPortForwardingField.INTERNAL_PORT not in rule

    def test_bad_internal_ip_omitted(self) -> None:
        """An unparseable internal IP is dropped."""

        raw = "&#60x&#6280&#62nope&#628080&#62TCP&#62"
        result = translate_state({"vts_rulelist": raw})
        [rule] = result[ARPortForwardingField.RULES]
        assert ARPortForwardingField.INTERNAL_IP not in rule

    def test_short_row(self) -> None:
        """A truncated row yields UNKNOWN protocol without raising."""

        result = translate_state({"vts_rulelist": "&#60x&#6280"})
        [rule] = result[ARPortForwardingField.RULES]
        assert rule[ARPortForwardingField.PROTOCOL] is (
            ARPortForwardingProtocol.UNKNOWN
        )

    def test_secondary_wan(self) -> None:
        """Secondary WAN rules are tagged with wan_unit 1."""

        result = translate_state(
            {"vts_rulelist": _RULE_TCP, "vts1_rulelist": _RULE_OTHER}
        )
        rules = result[ARPortForwardingField.RULES]
        assert [r[ARPortForwardingField.WAN_UNIT] for r in rules] == [0, 1]

    def test_non_string_list(self) -> None:
        """A non-string rule list contributes no rules."""

        result = translate_state({"vts_enable_x": "1", "vts_rulelist": 123})
        assert result[ARPortForwardingField.RULES] == []


class TestSerializeRules:
    """Tests for serialize_rules."""

    def test_empty(self) -> None:
        """An empty list serializes to an empty string."""

        assert serialize_rules([]) == ""

    def test_tcp_rule(self) -> None:
        """A TCP rule serializes to its ordered columns."""

        rule = {
            ARPortForwardingField.NAME: "Web",
            ARPortForwardingField.PROTOCOL: ARPortForwardingProtocol.TCP,
            ARPortForwardingField.EXTERNAL_PORT: "80",
            ARPortForwardingField.INTERNAL_IP: "192.168.1.10",
            ARPortForwardingField.INTERNAL_PORT: "8080",
        }
        assert serialize_rules([rule]) == "<Web>80>192.168.1.10>8080>TCP>"

    def test_other_uses_protocol_number(self) -> None:
        """OTHER serializes the protocol number into the external slot."""

        rule = {
            ARPortForwardingField.NAME: "GRE",
            ARPortForwardingField.PROTOCOL: ARPortForwardingProtocol.OTHER,
            ARPortForwardingField.PROTOCOL_NUMBER: 47,
            ARPortForwardingField.INTERNAL_IP: "192.168.1.20",
        }
        assert serialize_rules([rule]) == "<GRE>47>192.168.1.20>>OTHER>"

    @pytest.mark.parametrize("raw", [_RULE_TCP, _RULE_OTHER, _RULE_SOURCE])
    def test_round_trip(self, raw: str) -> None:
        """Parsing then serializing reproduces the decoded rule row."""

        rules = translate_state({"vts_rulelist": raw})[
            ARPortForwardingField.RULES
        ]
        decoded = raw.replace("&#60", "<").replace("&#62", ">")
        assert serialize_rules(rules) == decoded
