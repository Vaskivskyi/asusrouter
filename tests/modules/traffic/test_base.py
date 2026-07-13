"""Tests for the traffic base module."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.source import ARDataSource
from asusrouter.modules.traffic.base import ARTrafficSource, ARTrafficType
from asusrouter.modules.wifi import ARWiFiBand
from asusrouter.tools.identifiers import MacAddress

_TARGET = "AA:BB:CC:00:00:01"
_OTHER = "AA:BB:CC:00:00:02"


class TestARTrafficSource:
    """Tests for the traffic source."""

    def test_is_data_source(self) -> None:
        """The source subclasses ARDataSource."""

        assert issubclass(ARTrafficSource, ARDataSource)

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (_TARGET, MacAddress(_TARGET)),
            (MacAddress(_TARGET), MacAddress(_TARGET)),
            (None, None),
            ("not-a-mac", None),
        ],
        ids=["str", "macaddress", "none", "invalid"],
    )
    def test_target_coercion(
        self, value: Any, expected: MacAddress | None
    ) -> None:
        """Target coerces any input to MacAddress or None."""

        assert ARTrafficSource(target=value).target == expected

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (None, None),
            (ARTrafficType.WIRED, ARTrafficType.WIRED),
            (ARWiFiBand.BAND_5G1, ARWiFiBand.BAND_5G1),
            ("wired", ARTrafficType.WIRED),
            ("backhaul", ARTrafficType.BACKHAUL),
            ("5g1", ARWiFiBand.BAND_5G1),
            ("garbage", None),
        ],
        ids=[
            "none",
            "type",
            "band",
            "str-type",
            "str-backhaul",
            "str-band",
            "invalid",
        ],
    )
    def test_link_coercion(self, value: Any, expected: Any) -> None:
        """Link coerces to a type / band (band preferred) or None."""

        assert ARTrafficSource(link=value).link == expected

    def test_repr(self) -> None:
        """Repr includes the target and link key fields."""

        source = ARTrafficSource(ARTrafficType.WIRED, _TARGET)
        text = repr(source)

        assert text.startswith("<ARTrafficSource ")
        assert repr(source.target) in text
        assert repr(source.link) in text

    def test_equal_and_hash(self) -> None:
        """Equal by type, target and link; hash matches."""

        one = ARTrafficSource(ARTrafficType.WIRED, _TARGET)
        same = ARTrafficSource(ARTrafficType.WIRED, _TARGET)

        assert one == same
        assert hash(one) == hash(same)

    @pytest.mark.parametrize(
        "other",
        [
            ARTrafficSource(ARTrafficType.WAN, _TARGET),
            ARTrafficSource(ARTrafficType.WIRED, _OTHER),
        ],
        ids=["link", "target"],
    )
    def test_not_equal(self, other: ARTrafficSource) -> None:
        """Differing target or link makes sources unequal."""

        assert ARTrafficSource(ARTrafficType.WIRED, _TARGET) != other

    def test_not_equal_other_type(self) -> None:
        """Comparing to a non-source is not equal."""

        assert ARTrafficSource(target=_TARGET) != "not-a-source"

    def test_subclass_not_equal(self) -> None:
        """A subclass instance is never equal to the base."""

        class _Sub(ARTrafficSource):
            pass

        assert ARTrafficSource(target=_TARGET) != _Sub(target=_TARGET)
