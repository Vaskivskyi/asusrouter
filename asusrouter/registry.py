"""AsusRouter Registry."""

from __future__ import annotations

import threading
from typing import Any

from asusrouter.const import AR_CALL_GET_STATE, AR_CALL_TRANSLATE_STATE
from asusrouter.tools.types import ARCallableType

ARCallableEntry = ARCallableType | tuple[ARCallableType, bool]


class ARCallableRegistryBase:
    """Simple, thread-safe registry mapping source classes -> named callables.

    - Modules register their functions explicitly.
    - Lookup resolves by class then MRO (most-specific first).
    """

    def __init__(self) -> None:
        """Initialize the registry."""

        self._map: dict[type, dict[str, ARCallableEntry]] = {}
        self._flags: dict[ARCallableType, bool] = {}
        self._lock = threading.Lock()

    def register(self, source_cls: type, **callables: ARCallableEntry) -> None:
        """Register one or more named callables for `source_cls`."""

        with self._lock:
            entry = self._map.setdefault(source_cls, {})
            for name, value in callables.items():
                entry[name] = value
                if isinstance(value, tuple):
                    self._flags[value[0]] = bool(value[1])
                elif callable(value):
                    # Plain callables carry no flag; drop any stale one
                    self._flags.pop(value, None)

    def register_module(
        self,
        source_cls: type,
        *,
        get_state: ARCallableType | None = None,
        translate_state: ARCallableType | None = None,
        multi: bool = False,
    ) -> None:
        """Register a module's standard callables for `source_cls`."""

        callables: dict[str, ARCallableEntry] = {
            name: (func, True) if multi else func
            for name, func in (
                (AR_CALL_GET_STATE, get_state),
                (AR_CALL_TRANSLATE_STATE, translate_state),
            )
            if func is not None
        }
        self.register(source_cls, **callables)

    def unregister(self, source_cls: type) -> None:
        """Remove all registrations for a source class."""

        with self._lock:
            self._map.pop(source_cls, None)
            self._rebuild_flags()

    def clear(self) -> None:
        """Clear all registrations."""

        with self._lock:
            self._map.clear()
            self._flags.clear()

    def _rebuild_flags(self) -> None:
        """Rebuild callable flag mapping from registered entries."""

        self._flags.clear()
        for entry in self._map.values():
            for value in entry.values():
                if isinstance(value, tuple):
                    self._flags[value[0]] = bool(value[1])

    def _resolve_entry(self, source: Any, name: str) -> ARCallableEntry | None:
        """Resolve a registered entry for `source` and `name` by MRO."""

        cls = source if isinstance(source, type) else type(source)
        for base in cls.__mro__:
            entry = self._map.get(base)
            if entry and name in entry:
                return entry[name]
        return None

    def get_callable(self, source: Any, name: str) -> ARCallableType | None:
        """Return the callable for `source` (instance or class) or None.

        Resolves by checking the exact class and then walking the MRO.
        """

        with self._lock:
            value = self._resolve_entry(source, name)
            if value is None:
                return None
            return value[0] if isinstance(value, tuple) else value

    def get_callable_flag(self, source: Any, name: str | None = None) -> bool:
        """Return the callable flag for `source` or callable.

        If `source` is a callable and `name` is omitted, the stored flag for
        that callable is returned. Otherwise `source` is treated as a class or
        instance and `name` resolves the registered callable entry.
        """

        with self._lock:
            if name is None and callable(source):
                return self._flags.get(source, False)

            if name is None:
                return False

            value = self._resolve_entry(source, name)
            if value is None:
                return False
            if isinstance(value, tuple):
                return bool(value[1])
            return self._flags.get(value, False)

    def get_all_for(self, source: Any) -> dict[str, ARCallableEntry]:
        """Return all resolved callables for `source` by name (MRO merged).

        More specific classes override less specific ones.
        """

        cls = source if isinstance(source, type) else type(source)
        merged: dict[str, ARCallableEntry] = {}
        with self._lock:
            # walk MRO from base -> subclass so subclasses override
            for base in reversed(cls.__mro__):
                entry = self._map.get(base)
                if entry:
                    merged.update(entry)
        return merged


ARCallableRegistry: ARCallableRegistryBase = ARCallableRegistryBase()
