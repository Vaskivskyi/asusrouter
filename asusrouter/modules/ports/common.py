"""Shared helpers for the ports module."""

from __future__ import annotations

import logging
import threading

_LOGGER = logging.getLogger(__name__)

# Raw port labels already reported as unknown, to warn only once each
_reported_unknown_ports: set[str] = set()
_unknown_ports_lock = threading.Lock()


def warn_unknown_port(value: str) -> None:
    """Warn once per distinct unknown raw port label."""

    with _unknown_ports_lock:
        if value in _reported_unknown_ports:
            return
        _reported_unknown_ports.add(value)
        _LOGGER.warning(
            "We found an unknown port type. Please, report this value: `%s`",
            value,
        )
