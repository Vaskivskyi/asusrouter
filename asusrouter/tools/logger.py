"""Logger module for AsusRouter.

This module is needed to add a TRACE logging level to the logger,
which provides more information than DEBUG. In general, this information
is not needed for general use, but can help in tracing issues.

This module also adds an UNSAFE logging level, which can provide sensitive
information, including passwords. Not recommended for general use."""

from __future__ import annotations

import logging

TRACE = 5
UNSAFE = 3

logging.addLevelName(TRACE, "TRACE")
logging.addLevelName(UNSAFE, "UNSAFE")


def trace(self, message, *args, **kws):
    """Trace logging level."""

    if self.isEnabledFor(TRACE):
        self._log(TRACE, message, args, **kws)  # pylint: disable=protected-access


def unsafe(self, message, *args, **kws):
    """Unsafe logging level."""

    if self.isEnabledFor(UNSAFE):
        self._log(UNSAFE, message, args, **kws)  # pylint: disable=protected-access


logging.Logger.trace = trace
logging.Logger.unsafe = unsafe
