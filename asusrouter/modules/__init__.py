"""Modules for AsusRouter."""

from __future__ import annotations

import importlib
import logging
import pkgutil

_LOGGER = logging.getLogger(__name__)

# Source registration lives in
_SOURCE_MODULE = "source"
# Probe registration lives in
_PROBE_MODULE = "probe"


def _load_modules(module: str) -> None:
    """Import every module's `module` submodule to run its registrations."""

    for info in pkgutil.walk_packages(__path__, f"{__name__}."):
        if info.name.rsplit(".", 1)[-1] != module:
            continue
        try:
            importlib.import_module(info.name)
        except ImportError:
            _LOGGER.debug("Could not import module %s", info.name)


def load_all_probes() -> None:
    """Import every module's probe registrations."""

    _load_modules(_PROBE_MODULE)


def load_all_sources() -> None:
    """Import every module's source registrations."""

    _load_modules(_SOURCE_MODULE)
