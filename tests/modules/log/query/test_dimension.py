"""Tests for query dimensions over log events."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.common.command import ARService
from asusrouter.modules.log.enums import AREventKey, ARProgram
from asusrouter.modules.log.query.dimension import (
    QUERYABLE,
    coerce,
    extract_facets,
    has,
    resolve,
)
from asusrouter.modules.log.query.event import ARLogEvent
from asusrouter.modules.log.translate.ntp import AREventNtp
from asusrouter.tools.identifiers import MacAddress

_MAC = MacAddress("aa:bb:cc:00:00:01")


def _event(**overrides: Any) -> ARLogEvent:
    """Build an envelope with sensible defaults."""

    base: dict[str, Any] = {
        "timestamp": None,
        "program": ARProgram.NTP,
        "program_name": "ntp",
        "event_type": AREventNtp.START_UPDATE,
        "raw": "",
        "data": {},
    }
    base.update(overrides)

    return ARLogEvent(**base)


class TestCoerce:
    """Normalizing a query value to a dimension's type."""

    def test_mac_normalizes_format(self) -> None:
        """A dash-form MAC coerces to the canonical MacAddress."""

        assert coerce(AREventKey.CLIENT_MAC, "aa-bb-cc-00-00-01") == _MAC

    def test_program_from_string(self) -> None:
        """A raw program name coerces to the typed program."""

        assert coerce(AREventKey.PROGRAM, "ntp") is ARProgram.NTP

    def test_identity_for_plain_dimension(self) -> None:
        """A dimension without a coercer keeps the value as-is."""

        assert coerce(AREventKey.CALLER, "udhcpc") == "udhcpc"


class TestExtractFacets:
    """Deriving queryable facets from event data."""

    def test_scalar_field(self) -> None:
        """A facetable scalar field becomes one `(axis, value)` facet."""

        facets = extract_facets({AREventKey.CLIENT_MAC: _MAC})

        assert facets == frozenset({(AREventKey.CLIENT_MAC, _MAC)})

    def test_non_facetable_field_ignored(self) -> None:
        """A field that is not a queryable axis yields no facet."""

        assert extract_facets({AREventKey.VERSION: "1.2.3"}) == frozenset()

    def test_collection_expands_to_axis(self) -> None:
        """A list field expands to one facet per value under its axis."""

        facets = extract_facets(
            {AREventKey.SERVICES: ("restart_wan", "restart_firewall")}
        )

        assert facets == frozenset(
            {
                (AREventKey.SERVICE, "restart_wan"),
                (AREventKey.SERVICE, "restart_firewall"),
            }
        )

    def test_string_not_flattened(self) -> None:
        """A string value stays whole, not split into characters."""

        facets = extract_facets({AREventKey.INTERFACE: "br0"})

        assert facets == frozenset({(AREventKey.INTERFACE, "br0")})

    def test_none_skipped(self) -> None:
        """A None value produces no facet."""

        assert extract_facets({AREventKey.CLIENT_MAC: None}) == frozenset()

    def test_shared_axis_merges(self) -> None:
        """Two fields mapping to one axis both contribute facets."""

        facets = extract_facets(
            {
                AREventKey.SERVICE: "restart_wan",
                AREventKey.SERVICES: ("restart_firewall",),
            }
        )

        assert facets == frozenset(
            {
                (AREventKey.SERVICE, "restart_wan"),
                (AREventKey.SERVICE, "restart_firewall"),
            }
        )


class TestHas:
    """Testing whether an event carries a value on a dimension."""

    def test_program_dimension(self) -> None:
        """PROGRAM is tested against the envelope."""

        assert has(_event(), AREventKey.PROGRAM, ARProgram.NTP) is True
        assert has(_event(), AREventKey.PROGRAM, ARProgram.KERNEL) is False

    def test_event_type_dimension(self) -> None:
        """EVENT_TYPE is tested against the envelope."""

        event = _event()

        assert has(event, AREventKey.EVENT_TYPE, AREventNtp.START_UPDATE)
        assert not has(event, AREventKey.EVENT_TYPE, AREventNtp.UNKNOWN)

    def test_facet_axis(self) -> None:
        """A facet axis is tested against the facet set."""

        event = _event(data={AREventKey.CLIENT_MAC: _MAC})

        assert has(event, AREventKey.CLIENT_MAC, _MAC) is True

    def test_absent_axis(self) -> None:
        """A dimension the event lacks never matches."""

        assert has(_event(), AREventKey.CLIENT_MAC, _MAC) is False

    def test_value_on_other_axis(self) -> None:
        """A value carried on a different axis does not match."""

        event = _event(data={AREventKey.NODE_MAC: _MAC})

        assert has(event, AREventKey.CLIENT_MAC, _MAC) is False

    def test_multi_valued_axis(self) -> None:
        """Any value of a multi-valued axis matches."""

        event = _event(
            data={
                AREventKey.SERVICES: (
                    ARService.WAN_RESTART,
                    ARService.FIREWALL_RESTART,
                )
            }
        )

        assert has(event, AREventKey.SERVICE, ARService.WAN_RESTART)
        assert has(event, AREventKey.SERVICE, ARService.FIREWALL_RESTART)
        assert not has(event, AREventKey.SERVICE, ARService.REBOOT)


class TestResolve:
    """Extracting an event's value(s) on a dimension."""

    def test_program_dimension(self) -> None:
        """PROGRAM resolves off the envelope."""

        assert resolve(_event(), AREventKey.PROGRAM) == frozenset(
            {ARProgram.NTP}
        )

    def test_program_name_dimension(self) -> None:
        """PROGRAM_NAME resolves off the envelope, not the facet set."""

        assert resolve(_event(), AREventKey.PROGRAM_NAME) == frozenset({"ntp"})

    def test_event_type_dimension(self) -> None:
        """EVENT_TYPE resolves off the envelope."""

        assert resolve(_event(), AREventKey.EVENT_TYPE) == frozenset(
            {AREventNtp.START_UPDATE}
        )

    def test_facet_axis(self) -> None:
        """A facet axis resolves off the facet set."""

        event = _event(data={AREventKey.CLIENT_MAC: _MAC})

        assert resolve(event, AREventKey.CLIENT_MAC) == frozenset({_MAC})

    def test_absent_axis_is_empty(self) -> None:
        """A dimension the event lacks resolves to an empty set."""

        assert resolve(_event(), AREventKey.CLIENT_MAC) == frozenset()

    def test_multi_valued_axis(self) -> None:
        """An axis with several facets resolves to every value."""

        event = _event(
            data={
                AREventKey.SERVICES: (
                    ARService.WAN_RESTART,
                    ARService.FIREWALL_RESTART,
                )
            }
        )

        assert resolve(event, AREventKey.SERVICE) == frozenset(
            {ARService.WAN_RESTART, ARService.FIREWALL_RESTART}
        )


class TestQueryable:
    """The public list of axes a query may name."""

    def test_holds_envelope_and_facet_axes(self) -> None:
        """Both the envelope dimensions and the facet axes are listed."""

        assert AREventKey.PROGRAM in QUERYABLE
        assert AREventKey.EVENT_TYPE in QUERYABLE
        assert AREventKey.CLIENT_MAC in QUERYABLE

    def test_omits_plain_data_fields(self) -> None:
        """A field carried but not indexed is not queryable."""

        assert AREventKey.VERSION not in QUERYABLE

    def test_lists_the_axis_not_the_source_field(self) -> None:
        """`SERVICES` feeds the `SERVICE` axis, so only the axis is named."""

        assert AREventKey.SERVICE in QUERYABLE
        assert AREventKey.SERVICES not in QUERYABLE
