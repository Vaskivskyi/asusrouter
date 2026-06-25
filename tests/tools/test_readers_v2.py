"""Tests for the readers V2 tools."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.tools.readers_v2 import read_js_section, read_netdev


@pytest.mark.parametrize(
    ("data", "key", "expected"),
    [
        ({"a": [{"x": 1}]}, "a", {"x": 1}),
        ({"a": [[1, 2]]}, "a", [1, 2]),
        ({"a": []}, "a", None),
        ({"a": "x"}, "a", None),
        ({}, "a", None),
        ("not-a-dict", "a", None),
    ],
    ids=["dict", "list", "empty", "not_list", "absent", "not_dict"],
)
def test_read_js_section(data: Any, key: str, expected: Any) -> None:
    """The first element of a list-cover section is returned, else None."""

    assert read_js_section(data, key) == expected


class TestReadNetdev:
    """Tests for read_netdev."""

    def test_parses_interfaces(self) -> None:
        """Each interface yields integer rx/tx from hex."""

        content = (
            "netdev = {\n 'WIRED':{rx:0x0a,tx:0x14}\n"
            ",'WIRELESS0':{rx:0xff,tx:0x01}\n}"
        )

        assert read_netdev(content) == {
            "WIRED": {"rx": 10, "tx": 20},
            "WIRELESS0": {"rx": 255, "tx": 1},
        }

    def test_sums_duplicate_internet(self) -> None:
        """Duplicate INTERNET entries (dual-WAN) are summed."""

        content = (
            "netdev = {\n 'INTERNET':{rx:0x10,tx:0x20}\n"
            ",'INTERNET':{rx:0x01,tx:0x02}\n}"
        )

        assert read_netdev(content) == {"INTERNET": {"rx": 17, "tx": 34}}

    def test_parses_flat_appget_form(self) -> None:
        """The flat appGet `IFACE_rx` form is parsed, duplicates summed."""

        content = (
            '{"netdev":{"INTERNET_rx":"0x0a","INTERNET_tx":"0x14",'
            '"INTERNET_rx":"0x01","INTERNET_tx":"0x02","WIRED_rx":"0x05"}}'
        )

        assert read_netdev(content) == {
            "INTERNET": {"rx": 11, "tx": 22},
            "WIRED": {"rx": 5},
        }

    @pytest.mark.parametrize(
        "content",
        ["", "netdev = {}", "garbage", "'X':{rx:0xZZ,tx:0x1}"],
        ids=["empty", "no_entries", "garbage", "bad_hex"],
    )
    def test_no_match_yields_empty(self, content: str) -> None:
        """Content without valid entries yields an empty dict."""

        assert read_netdev(content) == {}
