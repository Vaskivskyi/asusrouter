"""AsusRouter Registry."""

from __future__ import annotations

from collections.abc import Callable
import threading
from typing import Any

CallableType = Callable[..., Any]


class ARCallableRegistryBase:
    """Simple, thread-safe registry mapping source classes -> named callables.

    - Modules register their functions explicitly.
    - Lookup resolves by class then MRO (most-specific first).
    """

    def __init__(self) -> None:
        """Initialize the registry."""

        self._map: dict[type, dict[str, CallableType]] = {}
        self._lock = threading.RLock()

    def register(self, source_cls: type, **callables: CallableType) -> None:
        """Register one or more named callables for `source_cls`."""

        with self._lock:
            entry = self._map.setdefault(source_cls, {})
            entry.update(callables)

    def unregister(self, source_cls: type) -> None:
        """Remove all registrations for a source class."""

        with self._lock:
            self._map.pop(source_cls, None)

    def clear(self) -> None:
        """Clear all registrations."""

        with self._lock:
            self._map.clear()

    def get_callable(self, source: Any, name: str) -> CallableType | None:
        """Return the callable for `source` (instance or class) or None.

        Resolves by checking the exact class and then walking the MRO.
        """

        cls = source if isinstance(source, type) else type(source)
        with self._lock:
            for base in getattr(cls, "__mro__", ()):
                entry = self._map.get(base)
                if entry and name in entry:
                    return entry[name]
        return None

    def get_all_for(self, source: Any) -> dict[str, CallableType]:
        """Return all resolved callables for `source` by name (MRO merged).

        More specific classes override less specific ones.
        """

        cls = source if isinstance(source, type) else type(source)
        merged: dict[str, CallableType] = {}
        with self._lock:
            # walk MRO from base -> subclass so subclasses override
            for base in reversed(getattr(cls, "__mro__", ())):
                entry = self._map.get(base)
                if entry:
                    merged.update(entry)
        return merged


ARCallableRegistry: ARCallableRegistryBase = ARCallableRegistryBase()
