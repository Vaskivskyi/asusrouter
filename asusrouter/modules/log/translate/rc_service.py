"""Service dispatch (rc_service) log event translation for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.modules.common.command import ARService
from asusrouter.modules.log.enums import AREventKey
from asusrouter.modules.log.translate.pattern import (
    ARLogPattern,
    ARLogPatternSet,
)
from asusrouter.tools.enum import FromStrMixin


class AREventRcService(FromStrMixin, StrEnum):
    """Service dispatch event types."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    NOTIFY = "notify"
    WAITING = "waiting"


def _actions(text: str) -> tuple[str, ...]:
    """Split an action list, dropping what a trailing separator leaves."""

    return tuple(
        stripped for action in text.split(";") if (stripped := action.strip())
    )


def _service(action: str) -> ARService:
    """Map an action token to a service (arg after a space is dropped)."""

    return ARService.from_value(action.split(maxsplit=1)[0])


def _services(actions: tuple[str, ...]) -> tuple[ARService, ...]:
    """Map every action token to its service."""

    return tuple(_service(action) for action in actions)


def _text(value: str) -> str | None:
    """Keep a non-empty token, or nothing."""

    return value or None


PATTERNS = ARLogPatternSet(
    AREventRcService.UNKNOWN,
    (
        # `<caller> <pid>:notify_rc <action>[;<action>...]`; an action may
        # carry an argument, and may be absent from ARService
        ARLogPattern(
            AREventRcService.NOTIFY,
            r"(?P<caller>\S+)\s+(?P<pid>\d+):notify_rc\s+(?P<actions>.+)",
            convert={AREventKey.ACTIONS: _actions, AREventKey.PID: int},
            derive={AREventKey.SERVICES: (AREventKey.ACTIONS, _services)},
            marker="notify_rc",
        ),
        # `waitting "<action>"[(last_rc:<action>)] via <caller>` - the
        # firmware's own misspelling; `last_rc` only on newer builds
        ARLogPattern(
            AREventRcService.WAITING,
            r'waitting\s+"(?P<action>[^"]+)"'
            r"(?:\(last_rc:(?P<last_action>[^)]*)\))?"
            r"\s+via\s+(?P<caller>\S+)",
            convert={AREventKey.LAST_ACTION: _text},
            derive={
                AREventKey.LAST_SERVICE: (AREventKey.LAST_ACTION, _service),
                AREventKey.SERVICE: (AREventKey.ACTION, _service),
            },
            marker="waitting",
        ),
    ),
)
