"""Tests for automatic masking of sensitive data in logs."""

from __future__ import annotations

import gc
import logging

import pytest

from asusrouter.config import (
    ARConfig,
    ARConfigKey as ARConfKey,
    ARInstanceConfig,
)
from asusrouter.tools.identifiers import IpAddress, MacAddress, Password, Ssid
from asusrouter.tools.security import ARSecurityLevel
from asusrouter.tools.security.log import (
    SensitiveFilter,
    _PassiveHandler,
    _reset_log_masking,
    effective_log_level,
    install_log_masking,
    register_log_config,
    render_for_log,
    unregister_log_config,
)

_MAC = "aa:bb:cc:11:22:33"
_IP = "192.168.1.10"
_SSID = "my-network"
_PASSWORD = "s3cr3t"

_LOGGER_NAME = "asusrouter.test_log"


@pytest.fixture(autouse=True)
def _reset() -> None:
    """Reset config and masking install around each test."""

    ARConfig.reset()
    _reset_log_masking()
    yield
    ARConfig.reset()
    _reset_log_masking()


def _make_record(msg: object, *args: object) -> logging.LogRecord:
    """Build a debug log record."""

    return logging.LogRecord(
        name=_LOGGER_NAME,
        level=logging.DEBUG,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=args,
        exc_info=None,
    )


class TestSensitiveFilter:
    """Tests for the filter that masks record content."""

    def _apply(self, level: ARSecurityLevel, record: logging.LogRecord) -> str:
        """Run the filter at a level and return the rendered message."""

        ARConfig.set(ARConfKey.SECURITY_LEVEL_LOG, level)
        assert SensitiveFilter().filter(record) is True
        return record.getMessage()

    def test_mac_sanitized_is_masked(self) -> None:
        """MAC is replaced by a pseudo value at SANITIZED."""

        record = _make_record("mac=%s", MacAddress.from_value(_MAC))
        message = self._apply(ARSecurityLevel.SANITIZED, record)

        assert _MAC not in message
        assert "-=REDACTED=-" not in message

    def test_mac_reasonable_is_raw(self) -> None:
        """MAC is shown raw at REASONABLE."""

        record = _make_record("mac=%s", MacAddress.from_value(_MAC))
        message = self._apply(ARSecurityLevel.REASONABLE, record)

        assert message == f"mac={_MAC}"

    def test_mac_default_is_redacted(self) -> None:
        """MAC is redacted below SANITIZED."""

        record = _make_record("mac=%s", MacAddress.from_value(_MAC))
        message = self._apply(ARSecurityLevel.DEFAULT, record)

        assert message == "mac=-=REDACTED=-"

    def test_ip_sanitized_is_masked(self) -> None:
        """IP is replaced by a pseudo value at SANITIZED."""

        record = _make_record("ip=%s", IpAddress.from_value(_IP))
        message = self._apply(ARSecurityLevel.SANITIZED, record)

        assert _IP not in message
        assert "-=REDACTED=-" not in message

    def test_ssid_shown_by_default(self) -> None:
        """SSID is shown at DEFAULT."""

        record = _make_record("ssid=%s", Ssid(_SSID))
        message = self._apply(ARSecurityLevel.DEFAULT, record)

        assert message == f"ssid={_SSID}"

    def test_password_redacted_below_unsafe(self) -> None:
        """Password is redacted at every level below UNSAFE."""

        record = _make_record("pw=%s", Password(_PASSWORD))
        message = self._apply(ARSecurityLevel.REASONABLE, record)

        assert _PASSWORD not in message
        assert message == "pw=-=REDACTED=-"

    def test_password_never_raw_even_unsafe(self) -> None:
        """Password string form redacts even when rendered raw at UNSAFE."""

        record = _make_record("pw=%s", Password(_PASSWORD))
        message = self._apply(ARSecurityLevel.UNSAFE, record)

        assert _PASSWORD not in message

    def test_mapping_args_masked(self) -> None:
        """Sensitive values in mapping-style args are masked."""

        record = _make_record(
            "mac=%(mac)s", {"mac": MacAddress.from_value(_MAC)}
        )
        message = self._apply(ARSecurityLevel.DEFAULT, record)

        assert message == "mac=-=REDACTED=-"

    def test_sensitive_message_itself(self) -> None:
        """A sensitive value logged as the message is masked."""

        record = _make_record(MacAddress.from_value(_MAC))
        message = self._apply(ARSecurityLevel.DEFAULT, record)

        assert message == "-=REDACTED=-"

    def test_non_sensitive_untouched(self) -> None:
        """Plain values pass through unchanged."""

        record = _make_record("value=%s", 42)
        message = self._apply(ARSecurityLevel.STRICT, record)

        assert message == "value=42"

    def test_mapping_without_sensitive_untouched(self) -> None:
        """Mapping args without sensitive values are left as is."""

        record = _make_record("value=%(v)s", {"v": 42})
        message = self._apply(ARSecurityLevel.STRICT, record)

        assert message == "value=42"


class TestEffectiveLogLevel:
    """Tests for the most-restrictive-wins log level."""

    def test_global_only(self) -> None:
        """With no instances, the global level applies."""

        ARConfig.set(ARConfKey.SECURITY_LEVEL_LOG, ARSecurityLevel.REASONABLE)
        assert effective_log_level() is ARSecurityLevel.REASONABLE

    def test_stricter_instance_wins(self) -> None:
        """A stricter instance level constrains the global one."""

        ARConfig.set(ARConfKey.SECURITY_LEVEL_LOG, ARSecurityLevel.REASONABLE)
        strict = ARInstanceConfig(
            {ARConfKey.SECURITY_LEVEL_LOG: ARSecurityLevel.STRICT}
        )
        register_log_config(strict)

        assert effective_log_level() is ARSecurityLevel.STRICT

    def test_laxer_instance_does_not_loosen(self) -> None:
        """A laxer instance cannot loosen a stricter global level."""

        ARConfig.set(ARConfKey.SECURITY_LEVEL_LOG, ARSecurityLevel.SANITIZED)
        lax = ARInstanceConfig(
            {ARConfKey.SECURITY_LEVEL_LOG: ARSecurityLevel.UNSAFE}
        )
        register_log_config(lax)

        assert effective_log_level() is ARSecurityLevel.SANITIZED

    def test_min_across_multiple_instances(self) -> None:
        """The strictest across several instances wins."""

        ARConfig.set(ARConfKey.SECURITY_LEVEL_LOG, ARSecurityLevel.UNSAFE)
        a = ARInstanceConfig(
            {ARConfKey.SECURITY_LEVEL_LOG: ARSecurityLevel.REASONABLE}
        )
        b = ARInstanceConfig(
            {ARConfKey.SECURITY_LEVEL_LOG: ARSecurityLevel.SANITIZED}
        )
        register_log_config(a)
        register_log_config(b)

        assert effective_log_level() is ARSecurityLevel.SANITIZED

    def test_unregister(self) -> None:
        """Unregistering an instance removes its constraint."""

        ARConfig.set(ARConfKey.SECURITY_LEVEL_LOG, ARSecurityLevel.REASONABLE)
        strict = ARInstanceConfig(
            {ARConfKey.SECURITY_LEVEL_LOG: ARSecurityLevel.STRICT}
        )
        register_log_config(strict)
        assert effective_log_level() is ARSecurityLevel.STRICT

        unregister_log_config(strict)
        assert effective_log_level() is ARSecurityLevel.REASONABLE

    def test_dead_instance_drops_out(self) -> None:
        """A garbage-collected instance no longer constrains the level."""

        ARConfig.set(ARConfKey.SECURITY_LEVEL_LOG, ARSecurityLevel.REASONABLE)
        strict = ARInstanceConfig(
            {ARConfKey.SECURITY_LEVEL_LOG: ARSecurityLevel.STRICT}
        )
        register_log_config(strict)
        assert effective_log_level() is ARSecurityLevel.STRICT

        del strict
        gc.collect()
        assert effective_log_level() is ARSecurityLevel.REASONABLE


class TestRenderForLog:
    """Tests for rendering a value at the current log level."""

    def test_masks_at_current_level(self) -> None:
        """A MAC is rendered against the effective log level."""

        ARConfig.set(ARConfKey.SECURITY_LEVEL_LOG, ARSecurityLevel.SANITIZED)
        mac = MacAddress.from_value(_MAC)

        result = render_for_log(mac)

        assert isinstance(result, MacAddress)
        assert result == mac.mask()
        assert result != mac

    def test_reveals_at_high_level(self) -> None:
        """A MAC is revealed raw at REASONABLE."""

        ARConfig.set(ARConfKey.SECURITY_LEVEL_LOG, ARSecurityLevel.REASONABLE)
        mac = MacAddress.from_value(_MAC)

        assert render_for_log(mac) is mac

    def test_non_sensitive_passthrough(self) -> None:
        """A plain value passes through unchanged."""

        assert render_for_log("plain") == "plain"


class TestInstall:
    """Tests for installing the masking handler."""

    def test_install_adds_handler(self) -> None:
        """Install attaches a single passive handler with the filter."""

        install_log_masking()
        logger = logging.getLogger("asusrouter")

        passive = [
            h for h in logger.handlers if isinstance(h, _PassiveHandler)
        ]
        assert len(passive) == 1
        assert any(isinstance(f, SensitiveFilter) for f in passive[0].filters)

    def test_install_idempotent(self) -> None:
        """Installing twice does not add a second handler."""

        install_log_masking()
        install_log_masking()
        logger = logging.getLogger("asusrouter")

        passive = [
            h for h in logger.handlers if isinstance(h, _PassiveHandler)
        ]
        assert len(passive) == 1

    def test_passive_handler_emits_nothing(self) -> None:
        """The passive handler emit is a no-op."""

        # Simply calling emit must not raise
        _PassiveHandler().emit(_make_record("x"))

    def test_end_to_end_masks_before_app_handler(self) -> None:
        """A child log record is masked before an app handler formats it."""

        install_log_masking()

        # App-style capturing handler placed on the package logger after
        # the masking handler, so it observes the mutated record
        captured: list[str] = []

        class _Capture(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                captured.append(record.getMessage())

        package_logger = logging.getLogger("asusrouter")
        capture = _Capture()
        package_logger.addHandler(capture)
        try:
            ARConfig.set(
                ARConfKey.SECURITY_LEVEL_LOG, ARSecurityLevel.SANITIZED
            )
            child = logging.getLogger(_LOGGER_NAME)
            child.setLevel(logging.DEBUG)
            child.debug("mac=%s", MacAddress.from_value(_MAC))
        finally:
            package_logger.removeHandler(capture)

        assert len(captured) == 1
        assert _MAC not in captured[0]
        assert "-=REDACTED=-" not in captured[0]
