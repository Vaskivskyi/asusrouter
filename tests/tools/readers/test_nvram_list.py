"""Tests for the nvram-list readers."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.tools.readers.nvram_list import decode, get_field, split_rows


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
