"""Tests for static DHCP lease parsing and serialization."""

from __future__ import annotations

import pytest

from asusrouter.modules.static_dhcp import (
    ARStaticDHCPLayout,
    StaticDHCPLease,
    compile_static_dhcp_leases,
    normalize_static_dhcp_mac,
    parse_static_dhcp_leases,
)
from asusrouter.tools.identifiers import MacAddress


def test_parse_modern_and_legacy_rows() -> None:
    """Modern DNS/hostname and legacy hostname rows retain their layouts."""

    leases = parse_static_dhcp_leases(
        "<AA:BB:CC:DD:EE:FF>192.168.1.2>1.1.1.1>printer"
        "<11:22:33:44:55:66>192.168.1.3>scanner"
    )

    assert leases == [
        StaticDHCPLease(
            mac="AA:BB:CC:DD:EE:FF",
            ip="192.168.1.2",
            dns="1.1.1.1",
            hostname="printer",
        ),
        StaticDHCPLease(
            mac="11:22:33:44:55:66",
            ip="192.168.1.3",
            hostname="scanner",
        ),
    ]
    assert leases[0].layout is ARStaticDHCPLayout.MODERN
    assert leases[1].layout is ARStaticDHCPLayout.LEGACY


def test_parse_escaped_rows() -> None:
    """ASUS encoded delimiters are decoded before parsing."""

    [lease] = parse_static_dhcp_leases(
        "&#60AA:BB:CC:DD:EE:FF&#62192.168.1.2&#621.1.1.1&#62printer"
    )
    assert lease.hostname == "printer"
    assert lease.dns == "1.1.1.1"


@pytest.mark.parametrize(
    "content",
    [
        "<missing-ip>",
        "<AA:BB:CC:DD:EE:FF>192.168.1.2>x>host",
        "<AA:BB:CC:DD:EE:FF>192.168.1.2>>>extra",
        42,
    ],
)
def test_parse_rejects_unrecognized_rows(content: object) -> None:
    """No row can be silently omitted before a whole-list rewrite."""

    with pytest.raises(
        ValueError,
        match="Static DHCP|Unrecognized|Invalid IP",
    ):
        parse_static_dhcp_leases(content)  # type: ignore[arg-type]


def test_compile_accepts_any_iterable() -> None:
    """The declared Iterable API accepts a generator."""

    leases = (
        lease
        for lease in [
            StaticDHCPLease(
                mac="AA:BB:CC:DD:EE:FF",
                ip="192.168.1.2",
            )
        ]
    )
    assert compile_static_dhcp_leases(leases) == {
        "dhcp_staticlist": "<AA:BB:CC:DD:EE:FF>192.168.1.2",
        "dhcp_static_x": 1,
    }


def test_compile_preserves_layouts_and_disabled_state() -> None:
    """Serialization round-trips both firmware layouts and explicit state."""

    raw = (
        "<AA:BB:CC:DD:EE:FF>192.168.1.2>1.1.1.1>printer"
        "<11:22:33:44:55:66>192.168.1.3>scanner"
    )
    assert compile_static_dhcp_leases(
        parse_static_dhcp_leases(raw),
        enabled=False,
    ) == {
        "dhcp_staticlist": raw,
        "dhcp_static_x": 0,
    }


def test_literal_none_hostname_is_preserved() -> None:
    """The hostname text None is data, not a missing value."""

    assert compile_static_dhcp_leases(
        [
            StaticDHCPLease(
                mac="AA:BB:CC:DD:EE:FF",
                ip="192.168.1.2",
                hostname="None",
            )
        ]
    )["dhcp_staticlist"].endswith(">>None")


def test_numeric_mac_normalization_is_feature_local() -> None:
    """Static DHCP reads plain 12 digits as hex without changing MacAddress."""

    value = "112233445566"
    assert normalize_static_dhcp_mac(value) == "11:22:33:44:55:66"
    assert MacAddress.from_value(value).as_asus() != "11:22:33:44:55:66"


@pytest.mark.parametrize(
    "leases",
    [
        [
            StaticDHCPLease(
                mac="AA:BB:CC:DD:EE:FF",
                ip="192.168.1.2",
            ),
            StaticDHCPLease(
                mac="aabbccddeeff",
                ip="192.168.1.3",
            ),
        ],
        [
            StaticDHCPLease(
                mac="AA:BB:CC:DD:EE:FF",
                ip="192.168.1.2",
            ),
            StaticDHCPLease(
                mac="11:22:33:44:55:66",
                ip="192.168.1.2",
            ),
        ],
    ],
)
def test_compile_rejects_duplicates(
    leases: list[StaticDHCPLease],
) -> None:
    """Duplicate MAC or IP values cannot be pushed."""

    with pytest.raises(ValueError, match="Duplicate static DHCP"):
        compile_static_dhcp_leases(leases)
