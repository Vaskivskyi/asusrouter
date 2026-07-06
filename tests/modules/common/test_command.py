"""Tests for asusrouter.modules.common.command."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.common.command import (
    ACTION_MODE_KEY,
    RC_SERVICE_KEY,
    ARActionMode,
    ARService,
)


class TestKeys:
    """Tests for the request body keys."""

    def test_action_mode_key(self) -> None:
        """The action mode key matches the device field."""

        assert ACTION_MODE_KEY == "action_mode"

    def test_rc_service_key(self) -> None:
        """The rc_service key matches the device field."""

        assert RC_SERVICE_KEY == "rc_service"


class TestARActionMode:
    """Tests for ARActionMode."""

    def test_apply_value(self) -> None:
        """APPLY maps to its string value."""

        assert ARActionMode.APPLY.value == "apply"

    def test_aimesh_reboot_value(self) -> None:
        """AIMESH_REBOOT keeps the raw Asus string."""

        assert ARActionMode.AIMESH_REBOOT.value == "device_reboot"

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("apply", ARActionMode.APPLY),
            ("re_reconnect", ARActionMode.AIMESH_REBUILD),
            ("nonsense", ARActionMode.UNKNOWN),
            (None, ARActionMode.UNKNOWN),
        ],
    )
    def test_from_value(self, value: Any, expected: ARActionMode) -> None:
        """from_value maps known strings, falls back to UNKNOWN."""

        assert ARActionMode.from_value(value) == expected


class TestARService:
    """Tests for ARService."""

    def test_wireless_restart_value(self) -> None:
        """WIRELESS_RESTART maps to the raw Asus string."""

        assert ARService.WIRELESS_RESTART.value == "restart_wireless"

    def test_feature_domain_name_keeps_raw_value(self) -> None:
        """A feature-renamed member keeps the Asus daemon string."""

        assert ARService.AURA_RESTART.value == "restart_ledg"
        assert ARService.WEBUI_RESTART.value == "restart_httpd"

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("restart_wireless", ARService.WIRELESS_RESTART),
            ("restart_firewall", ARService.FIREWALL_RESTART),
            ("restart_sdn", ARService.SDN_RESTART),
            ("restart_unknown", ARService.UNKNOWN),
            (None, ARService.UNKNOWN),
        ],
    )
    def test_from_value(self, value: Any, expected: ARService) -> None:
        """from_value maps known strings, falls back to UNKNOWN."""

        assert ARService.from_value(value) == expected

    def test_str_is_raw_value(self) -> None:
        """Stringifying a member yields the raw service string."""

        assert str(ARService.SDN_RESTART) == "restart_sdn"
