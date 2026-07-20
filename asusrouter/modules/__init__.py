"""Modules for AsusRouter."""

from __future__ import annotations

import importlib
import logging
import pkgutil

_LOGGER = logging.getLogger(__name__)

# Source registration lives in
_SOURCE_MODULE = "source"


def load_all_sources() -> None:
    """Import every module's source registrations."""

    for info in pkgutil.walk_packages(__path__, f"{__name__}."):
        if info.name.rsplit(".", 1)[-1] != _SOURCE_MODULE:
            continue
        try:
            importlib.import_module(info.name)
        except ImportError:
            _LOGGER.debug("Could not import source module %s", info.name)
