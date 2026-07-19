"""Tests for the ping targets source."""

from __future__ import annotations

from unittest.mock import AsyncMock

from asusrouter.modules.nvram import ARNvramType
from asusrouter.modules.ping.targets import (
    ARPingTarget,
    ARPingTargetsSource,
    ARPingTargetsSourceUniversal,
    fetch_state,
    translate_state,
)
from asusrouter.modules.ping.targets.source import _parse_targets
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.identifiers.ip import IpAddress

_RAW = "<Cloudflare>1.1.1.1<Cloudflare>1.0.0.1<Google>8.8.8.8"


def _ip(value: str) -> IpAddress:
    """Build an Ip address from a string."""

    ip = IpAddress.from_value_safe(value)
    assert ip is not None
    return ip


def _target(name: str, ip: str) -> ARPingTarget:
    """Build a ping target."""

    return ARPingTarget(name=name, ip=_ip(ip))


def _list_callback(raw: str | None) -> AsyncMock:
    """Build a fetch_data_callback returning the given dns_ping_list value."""

    return AsyncMock(return_value={ARNvramType.DNS_PING_LIST: raw})


class TestParseTargets:
    """Tests for _parse_targets."""

    def test_parses_entries(self) -> None:
        """A raw value parses into ordered targets."""

        assert _parse_targets(_RAW) == [
            _target("Cloudflare", "1.1.1.1"),
            _target("Cloudflare", "1.0.0.1"),
            _target("Google", "8.8.8.8"),
        ]

    def test_decodes_html_entities(self) -> None:
        """A value fetched HTML-entity encoded parses correctly."""

        encoded = "&#60Cloudflare&#621.1.1.1&#60Google&#628.8.8.8"
        assert _parse_targets(encoded) == [
            _target("Cloudflare", "1.1.1.1"),
            _target("Google", "8.8.8.8"),
        ]

    def test_empty(self) -> None:
        """An empty value parses to no targets."""

        assert _parse_targets("") == []

    def test_skips_malformed(self) -> None:
        """Entries without a valid IP are skipped."""

        assert _parse_targets("<NoIp><Bad>not-an-ip<Ok>1.1.1.1") == [
            _target("Ok", "1.1.1.1")
        ]


class TestSource:
    """Tests for the targets source."""

    def test_equal_by_type(self) -> None:
        """Sources are equal by exact type."""

        assert ARPingTargetsSource() == ARPingTargetsSourceUniversal

    def test_registered(self) -> None:
        """The source resolves to the module fetch_state callable."""

        assert (
            ARCallReg.get_callable(ARPingTargetsSourceUniversal, "fetch_state")
            is fetch_state
        )


class TestGetState:
    """Tests for fetch_state."""

    async def test_no_data_callback(self) -> None:
        """Without a data callback nothing is fetched."""

        assert (
            await fetch_state(AsyncMock(), ARPingTargetsSourceUniversal) == {}
        )

    async def test_returns_raw(self) -> None:
        """The raw dns_ping_list value is returned."""

        result = await fetch_state(
            AsyncMock(),
            ARPingTargetsSourceUniversal,
            fetch_data_callback=_list_callback(_RAW),
        )
        assert result == _RAW

    async def test_non_dict_values(self) -> None:
        """A non-dict nvram reply yields no data."""

        result = await fetch_state(
            AsyncMock(),
            ARPingTargetsSourceUniversal,
            fetch_data_callback=AsyncMock(return_value=None),
        )
        assert result == {}


class TestTranslateState:
    """Tests for translate_state."""

    def test_parses_string(self) -> None:
        """A raw string translates into targets."""

        assert translate_state(_RAW) == _parse_targets(_RAW)

    def test_non_string(self) -> None:
        """A non-string yields an empty list."""

        assert translate_state(None) == []
