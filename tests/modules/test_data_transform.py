"""Tests for the data_transform module."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.data_transform import transform_wan
from asusrouter.modules.support.flag import ARSupportType
from asusrouter.modules.wan import ARWANCapability

# Support dicts used across tests
_NO_SUPPORT: dict[ARSupportType, Any] = {}
_DUALWAN_SUPPORT: dict[ARSupportType, Any] = {
    ARSupportType.WAN_CAPABILITIES: [ARWANCapability.DUALWAN]
}
_AGGREGATION_SUPPORT: dict[ARSupportType, Any] = {
    ARSupportType.WAN_CAPABILITIES: [ARWANCapability.AGGREGATION]
}
_BOTH_SUPPORT: dict[ARSupportType, Any] = {
    ARSupportType.WAN_CAPABILITIES: [
        ARWANCapability.DUALWAN,
        ARWANCapability.AGGREGATION,
    ]
}


class TestTransformWan:
    """Tests for transform_wan."""

    def test_none_support_returns_copy(self) -> None:
        """None support → copy of data with all keys preserved."""

        data = {"dualwan": True, "aggregation": False, "extra": 1}
        result = transform_wan(data, None)
        assert result == data
        assert result is not data

    def test_empty_support_returns_copy(self) -> None:
        """Empty support dict → copy of data with all keys preserved."""

        data = {"dualwan": True}
        result = transform_wan(data, {})
        assert result == data

    def test_no_dualwan_support_pops_dualwan(self) -> None:
        """DUALWAN not in capabilities → dualwan key removed."""

        # _AGGREGATION_SUPPORT is truthy and lacks DUALWAN
        data = {"dualwan": True, "aggregation": False}
        result = transform_wan(data, _AGGREGATION_SUPPORT)
        assert "dualwan" not in result
        assert "aggregation" in result

    def test_no_aggregation_support_pops_aggregation(self) -> None:
        """AGGREGATION not in capabilities → aggregation key removed."""

        data = {"dualwan": True, "aggregation": False}
        result = transform_wan(data, _DUALWAN_SUPPORT)
        assert "dualwan" in result
        assert "aggregation" not in result

    def test_dualwan_only_keeps_dualwan(self) -> None:
        """DUALWAN available → dualwan preserved; aggregation removed."""

        data = {"dualwan": True, "aggregation": False}
        result = transform_wan(data, _DUALWAN_SUPPORT)
        assert "dualwan" in result

    def test_both_capabilities_keeps_both(self) -> None:
        """Both DUALWAN and AGGREGATION available → both keys kept."""

        data = {"dualwan": True, "aggregation": True}
        result = transform_wan(data, _BOTH_SUPPORT)
        assert "dualwan" in result
        assert "aggregation" in result

    def test_missing_keys_not_error(self) -> None:
        """Keys already absent → pop is safe, no KeyError."""

        data: dict[str, Any] = {}
        result = transform_wan(data, _NO_SUPPORT)
        assert result == {}

    def test_returns_copy_not_original(self) -> None:
        """Always returns a copy, never mutates input."""

        data = {"dualwan": True}
        result = transform_wan(data, _BOTH_SUPPORT)
        assert result is not data
