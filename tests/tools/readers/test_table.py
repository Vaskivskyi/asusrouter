"""Tests for the table reader."""

from __future__ import annotations

from asusrouter.tools.converters.raw import raw_to_int, raw_to_str
from asusrouter.tools.readers.table import read_table


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
