"""Tests for the legacy system status parsing."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.common.metrics import ARMetricType as M
from asusrouter.modules.system_status import legacy

_KIB = 1024


@pytest.mark.parametrize(
    ("used", "total", "result"),
    [
        (5, 10, 50.0),  # normal usage
        (10, 10, 100.0),  # normal usage
        (3, 9, 33.33),  # round to 2 decimals
        (-1, 2, 0.0),  # negative usage not allowed
        (1, -2, 0.0),  # negative usage not allowed
        (-1, -1, 100.0),  # both negative values result in positive usage
        (1, 0, 0.0),  # zero total usage not allowed
        (0, 0, 0.0),  # zero total usage not allowed
    ],
)
def test_safe_usage(used: float, total: float, result: float) -> None:
    """Test _safe_usage helper."""

    assert legacy._safe_usage(used, total) == result


@pytest.mark.parametrize(
    ("used", "total", "prev_used", "prev_total", "result"),
    [
        (10, 20, 5, 10, 50.0),  # normal usage
        (10, 20, 10, 20, 0.0),  # no usage
        (6, 18, 3, 9, 33.33),  # round to 2 decimals
        (
            5,
            20,
            10,
            10,
            0.0,
        ),  # invalid case when current used is less than previous
        (
            10,
            20,
            5,
            25,
            0.0,
        ),  # invalid case when current total is less than previous
        (
            5,
            10,
            10,
            20,
            0.0,
        ),  # invalid case when current values are less than previous
    ],
)
def test_safe_usage_historic(
    used: float,
    total: float,
    prev_used: float,
    prev_total: float,
    result: float,
) -> None:
    """Test _safe_usage_historic helper."""

    assert (
        legacy._safe_usage_historic(used, total, prev_used, prev_total)
        == result
    )


class TestParseCpu:
    """Tests for parse_cpu."""

    def test_parses_each_core(self) -> None:
        """Sequential cores are parsed into (total, used) counters."""

        raw = {
            "cpu1_total": "100",
            "cpu1_usage": "10",
            "cpu2_total": "200",
            "cpu2_usage": "20",
        }

        assert legacy.parse_cpu(raw) == {1: (100, 10), 2: (200, 20)}

    def test_stops_at_missing_core(self) -> None:
        """Parsing stops at the first absent core index."""

        raw = {"cpu1_total": "100", "cpu1_usage": "10", "cpu3_total": "300"}

        assert legacy.parse_cpu(raw) == {1: (100, 10)}

    def test_skips_non_int_core(self) -> None:
        """A core with a non-integer value is dropped."""

        raw = {"cpu1_total": "oops", "cpu1_usage": "10"}

        assert legacy.parse_cpu(raw) == {}

    def test_empty(self) -> None:
        """No cpu keys yields no counters."""

        assert legacy.parse_cpu({}) == {}


class TestTranslateCpu:
    """Tests for translate_cpu."""

    def test_no_prev(self) -> None:
        """Without a previous sample no usage is produced."""

        assert legacy.translate_cpu({1: (100, 10)}, None) == (None, {})

    def test_no_now(self) -> None:
        """Without current counters no usage is produced."""

        assert legacy.translate_cpu({}, {1: (100, 10)}) == (None, {})

    def test_aggregate_and_cores(self) -> None:
        """Usage is the ratio of the per-core tick deltas."""

        now = {1: (200, 60), 2: (200, 40)}
        prev = {1: (100, 10), 2: (100, 20)}

        aggregate, cores = legacy.translate_cpu(now, prev)

        # core 1: 50 used / 100 total = 50%, core 2: 20 / 100 = 20%
        assert cores == {1: 50.0, 2: 20.0}
        # aggregate: 70 used / 200 total = 35%
        assert aggregate == 35.0

    def test_skips_core_absent_in_prev(self) -> None:
        """A core missing from the previous sample is skipped."""

        now = {1: (200, 60), 2: (200, 40)}
        prev = {1: (100, 10)}

        aggregate, cores = legacy.translate_cpu(now, prev)

        assert cores == {1: 50.0}
        assert aggregate == 50.0

    def test_no_overlapping_cores(self) -> None:
        """No shared cores between samples yields no usage."""

        assert legacy.translate_cpu({1: (200, 60)}, {2: (100, 10)}) == (
            None,
            {},
        )

    def test_counter_reset_clamps_to_zero(self) -> None:
        """A reboot (counters reset) yields 0 rather than a negative."""

        now = {1: (50, 5)}
        prev = {1: (100, 10)}

        aggregate, cores = legacy.translate_cpu(now, prev)

        assert cores == {1: 0.0}
        assert aggregate == 0.0


class TestParseRam:
    """Tests for parse_ram."""

    def test_converts_kib_to_bytes(self) -> None:
        """Memory sizes are converted from KiB to bytes with usage."""

        raw = {"mem_free": "400", "mem_total": "1000", "mem_used": "600"}

        ram = legacy.parse_ram(raw)

        assert ram[M.FREE] == 400 * _KIB
        assert ram[M.TOTAL] == 1000 * _KIB
        assert ram[M.USED] == 600 * _KIB
        assert ram[M.USAGE] == 60.0

    def test_no_usage_without_total(self) -> None:
        """Usage needs both used and total."""

        ram = legacy.parse_ram({"mem_used": "600"})

        assert ram == {M.USED: 600 * _KIB}

    @pytest.mark.parametrize(
        "raw",
        [{}, {"mem_total": "oops"}],
        ids=["empty", "non_int"],
    )
    def test_unusable(self, raw: dict[str, Any]) -> None:
        """Empty or unparseable memory data yields nothing."""

        assert legacy.parse_ram(raw) == {}
