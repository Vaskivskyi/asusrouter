"""Tests for asusrouter.modules source discovery."""

from __future__ import annotations

import logging

import pytest

from asusrouter import modules
from asusrouter.const import AR_CALL_FETCH_STATE
from asusrouter.modules import load_all_probes, load_all_sources
from asusrouter.modules.ddns.source import ARDdnsSource
from asusrouter.registry import ARCallableRegistry as ARCallReg


def test_load_all_probes_loads_probe_submodules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Probes load from the `probe` submodule."""

    seen: list[str] = []
    monkeypatch.setattr(modules, "_load_modules", seen.append)

    load_all_probes()

    assert seen == ["probe"]


def test_load_all_sources_registers_lazy_modules() -> None:
    """Loading imports source modules that are not eagerly imported."""

    load_all_sources()

    assert ARDdnsSource in ARCallReg.classes_with(AR_CALL_FETCH_STATE)


def test_load_all_sources_skips_unimportable(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An unimportable source module is logged and skipped, not raised."""

    real_import = modules.importlib.import_module

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name.endswith(".source"):
            raise ImportError("boom")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(modules.importlib, "import_module", fake_import)

    with caplog.at_level(logging.DEBUG):
        load_all_sources()

    assert any(
        "Could not import" in record.message for record in caplog.records
    )
