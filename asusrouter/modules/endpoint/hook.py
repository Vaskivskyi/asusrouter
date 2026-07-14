"""Hook endpoint module."""

from __future__ import annotations

import logging
from typing import Any

from asusrouter.modules.data import AsusData

_LOGGER = logging.getLogger(__name__)

_VPNC_PART_MIN_FIELDS = 7


def process(data: dict[str, Any]) -> dict[AsusData, Any]:
    """Process hook data."""

    # For this endpoint, the received data always depends on the sent request.
    # So, we need to check which data is available and process it accordingly.
    # Otherwise, we can accidentally overwrite the data with empty values.

    state: dict[AsusData, Any] = {}

    return state
