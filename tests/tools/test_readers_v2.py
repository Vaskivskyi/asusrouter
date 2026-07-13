"""Tests for the readers V2 tools."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.tools.converters_v2.raw import raw_to_int, raw_to_str
from asusrouter.tools.readers_v2 import read_js_section, read_netdev
from asusrouter.tools.readers_v2.nvram_list import (
    decode,
    get_field,
    split_rows,
)
from asusrouter.tools.readers_v2.table import read_table


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


class TestReadTable:
    """Tests for read_table."""

    _TABLE = (
        ("alpha", "FIELD_A", raw_to_str),
        ("beta", "FIELD_B", raw_to_int),
        ("gamma", "FIELD_C", raw_to_int),
    )

    def test_reads_fields(self) -> None:
        """Present values convert onto their fields; absent ones skip."""

        data = {"alpha": "x", "beta": "5"}
        assert read_table(data, self._TABLE) == {
            "FIELD_A": "x",
            "FIELD_B": 5,
        }

    def test_skips_empty_values(self) -> None:
        """Empty raw values and failed conversions are skipped."""

        data = {"alpha": "", "beta": "not-an-int", "gamma": "0"}
        assert read_table(data, self._TABLE) == {"FIELD_C": 0}

    def test_key_resolves_raw_key(self) -> None:
        """A key callable maps table keys to raw data keys."""

        data = {"alpha_1": "x", "beta_1": "5"}
        result = read_table(data, self._TABLE, key=lambda kind: f"{kind}_1")
        assert result == {"FIELD_A": "x", "FIELD_B": 5}

    def test_empty_data(self) -> None:
        """No matching data yields an empty dict."""

        assert read_table({}, self._TABLE) == {}


class TestDecode:
    """Tests for decode."""

    def test_decodes_separators(self) -> None:
        """Char-encoded separators decode to `<`/`>`."""

        assert decode("&#60a&#62b") == "<a>b"

    def test_plain_passthrough(self) -> None:
        """A plain string passes through unchanged."""

        assert decode("<a>b") == "<a>b"

    @pytest.mark.parametrize("raw", [None, 5, ["<a>"]])
    def test_non_string(self, raw: Any) -> None:
        """A non-string yields an empty string."""

        assert decode(raw) == ""


class TestSplitRows:
    """Tests for split_rows."""

    def test_splits_rows(self) -> None:
        """Rows split on `<`, decoded first."""

        assert split_rows("&#60a&#62b&#60c") == ["", "a>b", "c"]

    def test_keeps_empty_rows(self) -> None:
        """Empty rows are kept, so positional lists stay aligned."""

        assert split_rows("<a<<b") == ["", "a", "", "b"]

    @pytest.mark.parametrize("raw", [None, "", 5])
    def test_no_data(self, raw: Any) -> None:
        """No usable data yields no rows."""

        assert split_rows(raw) == []


class TestGetField:
    """Tests for get_field."""

    def test_present(self) -> None:
        """A present field is returned as-is."""

        assert get_field(["a", "b"], 1) == "b"

    def test_out_of_range(self) -> None:
        """An absent or negative index yields None."""

        assert get_field(["a"], 5) is None
        assert get_field(["a"], -1) is None
