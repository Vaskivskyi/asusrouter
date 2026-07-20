"""Raw request recorder for AsusRouter data dumps."""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from asusrouter.const import RequestType
    from asusrouter.modules.endpoint import AREndpoint


@dataclass(slots=True)
class ARDumpRequest:
    """A single recorded wire request and its raw reply."""

    order: int
    endpoint: AREndpoint
    request_type: RequestType
    payload: str | None
    content: str | None


class ARDumpRecorder:
    """Collect raw wire requests issued while resolving a source."""

    def __init__(self) -> None:
        """Initialize the recorder."""

        self._requests: list[ARDumpRequest] = []

    def record(
        self,
        endpoint: AREndpoint,
        request_type: RequestType,
        payload: str | None,
        content: str | None,
    ) -> None:
        """Record a single wire request and its raw reply."""

        self._requests.append(
            ARDumpRequest(
                order=len(self._requests),
                endpoint=endpoint,
                request_type=request_type,
                payload=payload,
                content=content,
            )
        )

    @property
    def requests(self) -> list[ARDumpRequest]:
        """Get the recorded requests in capture order."""

        return self._requests

    def __len__(self) -> int:
        """Get the number of recorded requests."""

        return len(self._requests)

    def __bool__(self) -> bool:
        """Whether anything was recorded."""

        return bool(self._requests)


# Recorder bound to the current async context; only the dump's own fetches
# (and their context-inheriting sub-tasks) see it, so concurrent unrelated
# traffic on the same router is never swept into a dump
_active_recorder: ContextVar[ARDumpRecorder | None] = ContextVar(
    "ar_dump_recorder", default=None
)


def active_recorder() -> ARDumpRecorder | None:
    """Return the recorder bound to the current context, if any."""

    return _active_recorder.get()


def bind_recorder(recorder: ARDumpRecorder) -> Token[ARDumpRecorder | None]:
    """Bind a recorder to the current context; returns a reset token."""

    return _active_recorder.set(recorder)


def unbind_recorder(token: Token[ARDumpRecorder | None]) -> None:
    """Restore the recorder bound before `bind_recorder`."""

    _active_recorder.reset(token)
