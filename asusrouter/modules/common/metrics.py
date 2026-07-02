"""Common metrics module for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin


class ARMetricType(FromStrMixin, StrEnum):
    """A measurable metric, reusable across modules."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    # General
    ACTIVE = "active"
    FREE = "free"
    TOTAL = "total"
    USAGE = "usage"
    USED = "used"

    # Latency
    LATENCY_AVG = "latency_avg"
    LATENCY_MAX = "latency_max"
    LATENCY_MIN = "latency_min"

    # Packets
    PACKET_LOSS = "packet_loss"
    PACKETS_RECEIVED = "packets_received"
    PACKETS_SENT = "packets_sent"

    # Traffic and rates
    PHY_RX_SPEED = "phy_rx_speed"
    PHY_TX_SPEED = "phy_tx_speed"
    RX = "rx"
    RX_SPEED = "rx_speed"
    RX_SPEED_AVG = "rx_speed_avg"
    TX = "tx"
    TX_SPEED = "tx_speed"
    TX_SPEED_AVG = "tx_speed_avg"
