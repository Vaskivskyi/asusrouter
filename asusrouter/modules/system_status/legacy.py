"""Legacy appGet cpu/ram parsing for AsusRouter.

CPU values are cumulative tick counters (usage = delta between samples);
memory values are absolute KiB.
"""

from __future__ import annotations

from typing import Any

from asusrouter.modules.common.metrics import ARMetricType
from asusrouter.modules.endpoint.hooks import ARHook, hook_request
from asusrouter.tools.converters.raw import raw_to_int
from asusrouter.tools.units import DataUnitConverter, UnitOfData

# appGet hook request for legacy cpu/ram data (connected router only)
LEGACY_REQUEST = hook_request(
    (ARHook.CPU_USAGE, "appobj"), (ARHook.MEMORY_USAGE, "appobj")
)

# Memory values are reported in KiB; convert them to bytes
_KIB_TO_BYTES = DataUnitConverter.converter_factory(
    UnitOfData.KIBIBYTE, UnitOfData.BYTE
)

# Raw memory (free, used) keys in preference order: Web-GUI shows
# simple_* (excludes buffers/cache), older FW lacks it
_RAM_FREE_USED: tuple[tuple[str, str], ...] = (
    ("simple_free", "simple_used"),
    ("mem_free", "mem_used"),
)
_RAM_TOTAL = "mem_total"

# Cumulative cpu tick counters per core: {core_index: (total, used)}
CpuCounters = dict[int, tuple[int, int]]


def _safe_usage(used: float, total: float) -> float:
    """Calculate usage in percents, clamping negatives to 0.0."""

    if total == 0:
        return 0.0

    usage = round(used / total * 100, 2)

    # Don't allow negative usage
    if usage < 0:
        return 0.0

    return usage


def _safe_usage_historic(
    used: float,
    total: float,
    prev_used: float,
    prev_total: float,
) -> float:
    """Calculate usage in percents for the difference between two samples."""

    used_diff = used - prev_used
    total_diff = total - prev_total

    # Don't allow negative differences
    if used_diff < 0 or total_diff < 0:
        return 0.0

    return _safe_usage(used_diff, total_diff)


def parse_cpu(raw: dict[str, Any]) -> CpuCounters:
    """Parse cumulative cpu tick counters per core."""

    counters: CpuCounters = {}
    core = 1
    while (total_key := f"cpu{core}_total") in raw:
        total = raw_to_int(raw[total_key])
        used = raw_to_int(raw.get(f"cpu{core}_usage"))
        if total is not None and used is not None:
            counters[core] = (total, used)
        core += 1

    return counters


def translate_cpu(
    now: CpuCounters, prev: CpuCounters | None
) -> tuple[float | None, dict[int, float]]:
    """Compute aggregate and per-core usage from counter deltas.

    A previous sample is required; without it no usage is produced.
    """

    if not now or not prev:
        return None, {}

    cores: dict[int, float] = {}
    agg_total = agg_used = 0
    agg_prev_total = agg_prev_used = 0
    for core, (total, used) in now.items():
        if core not in prev:
            continue
        prev_total, prev_used = prev[core]
        cores[core] = _safe_usage_historic(used, total, prev_used, prev_total)
        agg_total += total
        agg_used += used
        agg_prev_total += prev_total
        agg_prev_used += prev_used

    if not cores:
        return None, {}

    aggregate = _safe_usage_historic(
        agg_used, agg_total, agg_prev_used, agg_prev_total
    )

    return aggregate, cores


def _read_free_used(raw: dict[str, Any]) -> tuple[int | None, int | None]:
    """Read the first complete (free, used) pair, else the last partial."""

    free = used = None
    for free_key, used_key in _RAM_FREE_USED:
        free = raw_to_int(raw.get(free_key))
        used = raw_to_int(raw.get(used_key))
        if free is not None and used is not None:
            break

    return free, used


def parse_ram(raw: dict[str, Any]) -> dict[ARMetricType, float]:
    """Parse memory data, converting sizes from KiB to bytes."""

    free, used = _read_free_used(raw)
    total = raw_to_int(raw.get(_RAM_TOTAL))

    sizes = (
        (ARMetricType.FREE, free),
        (ARMetricType.TOTAL, total),
        (ARMetricType.USED, used),
    )
    ram: dict[ARMetricType, float] = {
        metric: int(_KIB_TO_BYTES(value))
        for metric, value in sizes
        if value is not None
    }
    if used is not None and total is not None:
        ram[ARMetricType.USAGE] = _safe_usage(used, total)

    return ram
