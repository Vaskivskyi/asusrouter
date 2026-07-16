"""Automatic masking of sensitive data in log records."""

from __future__ import annotations

import logging
import threading
from typing import Any
import weakref

from asusrouter.config import (
    ARConfig,
    ARConfigKey as ARConfKey,
    ARInstanceConfig,
)
from asusrouter.tools.security.level import ARSecurityLevel
from asusrouter.tools.security.sensitive import ARSensitive, render

# Marks the logger as already carrying the masking handler
_MASKING_FLAG = "_ar_sensitive_masking"

# Live instance configs whose log level constrains the shared log masking.
# Weak so dead instances drop out on their own.
_log_configs: weakref.WeakSet[ARInstanceConfig] = weakref.WeakSet()
_log_configs_lock = threading.Lock()


def register_log_config(config: ARInstanceConfig) -> None:
    """Register an instance config to constrain shared log masking."""

    with _log_configs_lock:
        _log_configs.add(config)


def unregister_log_config(config: ARInstanceConfig) -> None:
    """Remove an instance config from the log masking constraint."""

    with _log_configs_lock:
        _log_configs.discard(config)


def effective_log_level() -> ARSecurityLevel:
    """Return the most restrictive log level across global and instances.

    A record carries no instance identity, so the shared filter cannot know
    which instance emitted it. The strictest (lowest) level wins so that no
    instance's data leaks through a laxer one.
    """

    level: ARSecurityLevel = ARConfig.get(ARConfKey.SECURITY_LEVEL_LOG)

    with _log_configs_lock:
        configs = list(_log_configs)

    for config in configs:
        instance_level = config.get(ARConfKey.SECURITY_LEVEL_LOG)
        level = min(level, instance_level)

    return level


def render_for_log(value: Any) -> Any:
    """Render a value against the current effective log level.

    Use when a sensitive value must be embedded into a string (e.g. an
    exception message) that will later be logged: the log filter cannot
    reach values already formatted into text, so mask them beforehand.
    """

    return render(value, effective_log_level())


class SensitiveFilter(logging.Filter):
    """Render sensitive values in a log record per the log security level."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Mask sensitive message and arguments in place."""

        args = record.args
        msg_sensitive = isinstance(record.msg, ARSensitive)
        args_tuple = isinstance(args, tuple) and any(
            isinstance(arg, ARSensitive) for arg in args
        )
        args_dict = isinstance(args, dict) and any(
            isinstance(val, ARSensitive) for val in args.values()
        )

        # Most records carry nothing sensitive; skip the level lookup then
        if not (msg_sensitive or args_tuple or args_dict):
            return True

        level = effective_log_level()

        if msg_sensitive:
            record.msg = render(record.msg, level)
        if isinstance(args, tuple) and args_tuple:
            record.args = tuple(render(arg, level) for arg in args)
        elif isinstance(args, dict) and args_dict:
            record.args = {
                key: render(val, level) for key, val in args.items()
            }

        return True


class _PassiveHandler(logging.Handler):
    """Handler that runs its filters but emits nothing.

    It exists only to run `SensitiveFilter` on records propagating through
    the package logger, mutating them before they reach the app's handlers.
    """

    def emit(self, record: logging.LogRecord) -> None:
        """Do nothing - masking happens in the attached filter."""


def install_log_masking(logger_name: str = "asusrouter") -> None:
    """Attach sensitive-data masking to a package logger.

    Idempotent. Records from child loggers propagate through the attached
    handler, which masks sensitive values according to the log security
    level before the records reach any application handler.
    """

    logger = logging.getLogger(logger_name)
    if getattr(logger, _MASKING_FLAG, False):
        return

    handler = _PassiveHandler()
    handler.addFilter(SensitiveFilter())
    logger.addHandler(handler)
    setattr(logger, _MASKING_FLAG, True)


def _reset_log_masking(logger_name: str = "asusrouter") -> None:
    """Remove the masking handler from a logger (for tests)."""

    logger = logging.getLogger(logger_name)
    for handler in list(logger.handlers):
        if isinstance(handler, _PassiveHandler):
            logger.removeHandler(handler)
    if hasattr(logger, _MASKING_FLAG):
        delattr(logger, _MASKING_FLAG)
    with _log_configs_lock:
        _log_configs.clear()
