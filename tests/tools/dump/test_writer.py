"""Tests for asusrouter.tools.dump.writer."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from asusrouter.const import RequestType, __version__
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.firmware.version import ARFirmware
from asusrouter.modules.source import ARDataSource
from asusrouter.modules.support.flag import ARSupportType
from asusrouter.modules.wifi.enums import ARWiFiBand
from asusrouter.tools.dump.recorder import ARDumpRecorder
from asusrouter.tools.dump.writer import (
    _next_scenario,
    write_device_snapshot,
    write_dump,
)

_MODEL = "RT-AX88U"
_FIRMWARE_OBJ = ARFirmware(
    major=(3, 0, 0, 4), minor=388, build=24762, revision=1
)
_FIRMWARE = str(_FIRMWARE_OBJ)


class _DumpSource(ARDataSource):
    """A distinct source type for dump tests."""


def _identity(
    model: str | None = _MODEL,
    firmware: ARFirmware | None = None,
) -> ARDeviceIdentity:
    """Build a device identity with the given model and firmware."""

    identity = ARDeviceIdentity()
    identity._model = model
    identity._firmware = firmware or _FIRMWARE_OBJ
    return identity


def _recorder() -> ARDumpRecorder:
    """Build a recorder with two entries."""

    recorder = ARDumpRecorder()
    recorder.record(AREndpoint.FETCH_DATA, RequestType.POST, "hook=x", "body0")
    recorder.record(
        AREndpoint.FETCH_VPN_STATUS, RequestType.GET, None, "body1"
    )
    return recorder


class TestWriteDump:
    """Tests for write_dump."""

    def test_writes_tree(self, tmp_path: Path) -> None:
        """Writes meta plus a content/json pair per request."""

        scenario_dir = write_dump(
            _recorder(),
            path=tmp_path,
            identity=_identity(),
            source=_DumpSource(),
        )

        assert scenario_dir == (
            tmp_path / _MODEL / _FIRMWARE / "_DumpSource" / "000"
        )
        assert (scenario_dir / "00.content").read_text(
            encoding="utf-8"
        ) == "body0"
        assert (scenario_dir / "01.content").read_text(
            encoding="utf-8"
        ) == "body1"

    def test_request_json(self, tmp_path: Path) -> None:
        """Each request json records endpoint, type and payload."""

        scenario_dir = write_dump(
            _recorder(),
            path=tmp_path,
            identity=_identity(),
            source=_DumpSource(),
        )

        first = json.loads((scenario_dir / "00.json").read_text("utf-8"))
        assert first == {
            "order": 0,
            "endpoint": "FETCH_DATA",
            "request_type": "POST",
            "payload": "hook=x",
        }
        second = json.loads((scenario_dir / "01.json").read_text("utf-8"))
        assert second["endpoint"] == "FETCH_VPN_STATUS"
        assert second["payload"] is None

    def test_meta_json(self, tmp_path: Path) -> None:
        """Meta json records source identity and library version."""

        scenario_dir = write_dump(
            _recorder(),
            path=tmp_path,
            identity=_identity(),
            source=_DumpSource(),
        )

        meta = json.loads((scenario_dir / "meta.json").read_text("utf-8"))
        assert meta["source_class"] == "_DumpSource"
        assert meta["library_version"] == __version__
        assert "captured_at" in meta

    def test_scenario_increments(self, tmp_path: Path) -> None:
        """Repeated dumps allocate the next scenario index."""

        for _ in range(2):
            write_dump(
                _recorder(),
                path=tmp_path,
                identity=_identity(),
                source=_DumpSource(),
            )

        source_dir = tmp_path / _MODEL / _FIRMWARE / "_DumpSource"
        assert {child.name for child in source_dir.iterdir()} == {"000", "001"}

    @pytest.mark.parametrize(
        ("model", "firmware", "expected"),
        [
            (None, _FIRMWARE_OBJ, ("unknown", _FIRMWARE)),
            (
                _MODEL,
                ARFirmware(major=(3, 0, 0, 4), minor=388, build=24762),
                (_MODEL, "3.0.0.4.388.24762"),
            ),
            (_MODEL, ARFirmware(), (_MODEL, "unknown")),
            (None, ARFirmware(), ("unknown", "unknown")),
        ],
        ids=["no_model", "partial_firmware", "no_firmware", "no_identity"],
    )
    def test_incomplete_identity_falls_back(
        self,
        tmp_path: Path,
        model: str | None,
        firmware: ARFirmware,
        expected: tuple[str, str],
    ) -> None:
        """Missing identity parts fall back to `unknown`, keeping known."""

        scenario_dir = write_dump(
            _recorder(),
            path=tmp_path,
            identity=_identity(model=model, firmware=firmware),
            source=_DumpSource(),
        )

        model_dir, firmware_dir = expected
        assert scenario_dir == (
            tmp_path / model_dir / firmware_dir / "_DumpSource" / "000"
        )
        assert (scenario_dir / "00.content").read_text("utf-8") == "body0"


class TestWriteDeviceSnapshot:
    """Tests for write_device_snapshot."""

    def test_writes_snapshot(self, tmp_path: Path) -> None:
        """Writes model, firmware, support and wifi under the device dir."""

        identity = _identity()
        identity._support = {ARSupportType.AI: True}
        identity._wifi = {ARWiFiBand.BAND_2G1: 0}

        target = write_device_snapshot(tmp_path, identity)

        assert target == tmp_path / _MODEL / _FIRMWARE / "device.json"
        data = json.loads(target.read_text("utf-8"))
        assert data["model"] == _MODEL
        assert data["firmware"] == _FIRMWARE
        assert data["support"] == {"AI": True}
        assert data["wifi"] == {"BAND_2G1": 0}

    def test_unknown_identity_snapshot(self, tmp_path: Path) -> None:
        """Falls back to `unknown` dirs when identity is empty."""

        target = write_device_snapshot(tmp_path, ARDeviceIdentity())

        assert target == tmp_path / "unknown" / "unknown" / "device.json"

    def test_rog_firmware_dir(self, tmp_path: Path) -> None:
        """A ROG firmware keeps its `_rog` suffix in the path."""

        firmware = ARFirmware(
            major=(3, 0, 0, 4), minor=388, build=24762, rog=True
        )
        target = write_device_snapshot(tmp_path, _identity(firmware=firmware))

        assert target.parent.name == "3.0.0.4.388.24762_rog"


class TestNextScenario:
    """Tests for _next_scenario."""

    def test_missing_dir(self, tmp_path: Path) -> None:
        """A missing source directory starts at 000."""

        assert _next_scenario(tmp_path / "absent") == "000"

    def test_ignores_non_numeric(self, tmp_path: Path) -> None:
        """Non-numeric and file children are ignored."""

        (tmp_path / "001").mkdir()
        (tmp_path / "notes").mkdir()
        (tmp_path / "005.content").write_text("x", encoding="utf-8")

        assert _next_scenario(tmp_path) == "002"
