"""Legacy appGet cpu/ram parsing for AsusRouter.

CPU values are cumulative tick counters (usage = delta between samples);
memory values are absolute KiB.
"""

from __future__ import annotations

from typing import Any

from asusrouter.modules.metrics import ARMetricType
from asusrouter.tools.converters import safe_usage, safe_usage_historic
from asusrouter.tools.converters_v2.raw import raw_to_int
from asusrouter.tools.units import DataUnitConverter, UnitOfData

# appGet hook request for legacy cpu/ram data (connected router only)
LEGACY_REQUEST = "hook=cpu_usage(appobj);memory_usage(appobj)"

# Memory values are reported in KiB; convert them to bytes
_KIB_TO_BYTES = DataUnitConverter.converter_factory(
    UnitOfData.KIBIBYTE, UnitOfData.BYTE
)

# Cumulative cpu tick counters per core: {core_index: (total, used)}
CpuCounters = dict[int, tuple[int, int]]


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
        cores[core] = safe_usage_historic(used, total, prev_used, prev_total)
        agg_total += total
        agg_used += used
        agg_prev_total += prev_total
        agg_prev_used += prev_used

    if not cores:
        return None, {}

    aggregate = safe_usage_historic(
        agg_used, agg_total, agg_prev_used, agg_prev_total
    )

    return aggregate, cores


def parse_ram(raw: dict[str, Any]) -> dict[ARMetricType, float]:
    """Parse memory data, converting sizes from KiB to bytes."""

    free = raw_to_int(raw.get("mem_free"))
    total = raw_to_int(raw.get("mem_total"))
    used = raw_to_int(raw.get("mem_used"))

    ram: dict[ARMetricType, float] = {}
    if free is not None:
        ram[ARMetricType.FREE] = int(_KIB_TO_BYTES(free))
    if total is not None:
        ram[ARMetricType.TOTAL] = int(_KIB_TO_BYTES(total))
    if used is not None:
        ram[ARMetricType.USED] = int(_KIB_TO_BYTES(used))
    if used is not None and total is not None:
        ram[ARMetricType.USAGE] = safe_usage(used, total)

    return ram
