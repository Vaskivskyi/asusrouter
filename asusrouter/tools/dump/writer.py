"""Disk writer for AsusRouter data dumps."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from asusrouter.const import __version__

if TYPE_CHECKING:
    from asusrouter.modules.device.identity import ARDeviceIdentity
    from asusrouter.modules.firmware.version import ARFirmware
    from asusrouter.modules.source import ARDataSource, ARDataType
    from asusrouter.tools.dump.recorder import ARDumpRecorder

# Default root for dumped device data
DEFAULT_DUMP_PATH = "dumps"

# Emitted once per session before the first dump
DUMP_SENSITIVE_WARNING = (
    "Data dump created files that can contain sensitive information "
    "(MAC and IP addresses, SSIDs, serial numbers, credentials). "
    "Sanitize them before sharing"
)

# Path token for incomplete identity
UNKNOWN_IDENTITY = "unknown"


def _firmware_path(firmware: ARFirmware) -> str:
    """Filesystem name for a firmware, dropping unknown components."""

    parts: list[str] = []
    if firmware.major is not None:
        parts.append(".".join(str(part) for part in firmware.major))
    if firmware.minor is not None:
        parts.append(str(firmware.minor))
    if firmware.build is not None:
        parts.append(str(firmware.build))

    version = ".".join(parts)
    if firmware.revision is not None:
        revision = str(firmware.revision)
        version = f"{version}_{revision}" if version else revision
    if firmware.rog:
        version = f"{version}_rog" if version else "rog"

    return version or UNKNOWN_IDENTITY


def _next_scenario(source_dir: Path) -> str:
    """Return the next free numeric scenario directory name."""

    if not source_dir.is_dir():
        return "000"

    used = [
        int(child.name)
        for child in source_dir.iterdir()
        if child.is_dir() and child.name.isdigit()
    ]
    return f"{max(used, default=-1) + 1:03d}"


def _device_dir(path: str | Path, identity: ARDeviceIdentity) -> Path:
    """Return the `{path}/{model}/{firmware}` directory for a device."""

    model = identity.model or UNKNOWN_IDENTITY
    firmware = _firmware_path(identity.firmware)
    return Path(path) / model / firmware


def write_device_snapshot(
    path: str | Path, identity: ARDeviceIdentity
) -> Path:
    """Write the parsed device identity and capabilities snapshot.

    Gives the guard-relevant context (model, firmware, support flags, WiFi
    bands) that explains why sources fetched what they did on this device.
    """

    device_dir = _device_dir(path, identity)
    device_dir.mkdir(parents=True, exist_ok=True)

    firmware = identity.firmware
    snapshot: dict[str, Any] = {
        "model": identity.model,
        "model_original": identity.model_original,
        "brand": identity.brand,
        "firmware": str(firmware),
        "firmware_type": firmware.firmware_type.name,
        "support": {
            getattr(key, "name", str(key)): value
            for key, value in identity.support.items()
        },
        "wifi": {band.name: unit for band, unit in identity.wifi.items()},
    }

    target = device_dir / "device.json"
    _write_json(target, snapshot)
    return target


def write_dump(
    recorder: ARDumpRecorder,
    *,
    path: str | Path,
    identity: ARDeviceIdentity,
    source: ARDataSource | ARDataType,
) -> Path:
    """Write recorded requests into the device-test tree.

    Layout: `{path}/{model}/{firmware}/{SourceClass}/{scenario}/`, holding
    `meta.json` plus a `NN.content`/`NN.json` pair per recorded request.
    """

    source_dir = _device_dir(path, identity) / type(source).__name__
    scenario_dir = source_dir / _next_scenario(source_dir)
    scenario_dir.mkdir(parents=True)

    meta: dict[str, Any] = {
        "source_class": type(source).__name__,
        "source_repr": repr(source),
        "captured_at": datetime.now(UTC).isoformat(),
        "library_version": __version__,
    }
    _write_json(scenario_dir / "meta.json", meta)

    for request in recorder.requests:
        stem = f"{request.order:02d}"
        (scenario_dir / f"{stem}.content").write_text(
            request.content or "", encoding="utf-8"
        )
        _write_json(
            scenario_dir / f"{stem}.json",
            {
                "order": request.order,
                "endpoint": request.endpoint.name,
                "request_type": request.request_type.name,
                "payload": request.payload,
            },
        )

    return scenario_dir


def _write_json(path: Path, data: dict[str, Any]) -> None:
    """Write a JSON file with a trailing newline."""

    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
