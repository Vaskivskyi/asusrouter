"""Test registry module."""

from __future__ import annotations

from collections.abc import Callable, Generator
import threading
from typing import Any

import pytest

from asusrouter.registry import ARCallableRegistry as ARCallReg


@pytest.fixture(autouse=True)
def clear_registry() -> Generator[None, None, None]:
    """Ensure tests start with a clean registry state."""

    ARCallReg.clear()
    yield
    ARCallReg.clear()


def test_register_and_get_callable_by_instance_and_class() -> None:
    """Test registering and retrieving callables by instance and class."""

    class Base:
        pass

    class Child(Base):
        pass

    def base_get(s: Any) -> str:
        return "base"

    # register using kwargs API
    ARCallReg.register(Base, fetch_state=base_get)

    # lookup by instance
    fn = ARCallReg.get_callable(Child(), "fetch_state")
    assert fn is base_get
    assert fn is not None
    assert fn(Child()) == "base"

    # lookup by class
    fn2 = ARCallReg.get_callable(Child, "fetch_state")
    assert fn2 is base_get


def test_classes_with_lists_only_matching_names() -> None:
    """Test that classes_with returns classes registering the given name."""

    class A:
        pass

    class B:
        pass

    def fn(s: Any) -> None:
        return None

    ARCallReg.register(A, fetch_state=fn)
    ARCallReg.register(B, translate_state=fn)

    assert ARCallReg.classes_with("fetch_state") == [A]
    assert ARCallReg.classes_with("translate_state") == [B]
    assert ARCallReg.classes_with("run_action") == []


def test_get_all_for_merges_mro_correctly() -> None:
    """Test that get_all_for merges MRO correctly."""

    class A:
        pass

    class B(A):
        pass

    def a_get(s: Any) -> str:
        return "a"

    def b_get(s: Any) -> str:
        return "b"

    def a_set(s: Any, v: Any) -> tuple[str, Any]:
        return ("a-set", v)

    ARCallReg.register(A, fetch_state=a_get, set_state=a_set)
    ARCallReg.register(B, fetch_state=b_get)

    merged = ARCallReg.get_all_for(B())
    # B overrides fetch_state, but inherits set_state from A
    assert merged["fetch_state"] is b_get
    assert merged["set_state"] is a_set


def test_register_with_callable_flag_tuple() -> None:
    """Test registering callable entries with optional metadata."""

    class A:
        pass

    def fetch_state(s: Any) -> str:
        return "state"

    def set_state(s: Any, v: Any) -> str:
        return "set"

    ARCallReg.register(
        A,
        fetch_state=(fetch_state, True),
        set_state=set_state,
    )

    callable_result = ARCallReg.get_callable(A(), "fetch_state")
    assert callable_result is fetch_state

    assert ARCallReg.get_callable_flag(A(), "fetch_state") is True
    assert ARCallReg.get_callable_flag(A(), "set_state") is False
    assert ARCallReg.get_callable_flag(fetch_state) is True
    assert ARCallReg.get_callable_flag(set_state) is False

    all_map = ARCallReg.get_all_for(A())
    assert all_map["fetch_state"] == (fetch_state, True)
    assert all_map["set_state"] is set_state


def test_register_plain_callable_resets_flag_to_false() -> None:
    """Test that registering a plain callable clears a previous tuple flag."""

    class A:
        pass

    def fetch_state(s: Any) -> str:
        return "state"

    ARCallReg.register(A, fetch_state=(fetch_state, True))
    assert ARCallReg.get_callable_flag(fetch_state) is True

    ARCallReg.register(A, fetch_state=fetch_state)
    assert ARCallReg.get_callable_flag(fetch_state) is False
    assert ARCallReg.get_callable(A(), "fetch_state") is fetch_state


def test_register_action_registers_both_callables() -> None:
    """register_action wires run_action and translate_action by class."""

    class A:
        pass

    def run_action(callback: Any, action: Any) -> str:
        return "run"

    def translate_action(result: Any) -> str:
        return "translated"

    ARCallReg.register_action(
        A, run_action=run_action, translate_action=translate_action
    )

    assert ARCallReg.get_callable(A(), "run_action") is run_action
    assert ARCallReg.get_callable(A(), "translate_action") is translate_action


def test_register_action_skips_missing_callables() -> None:
    """register_action registers only the callables that are provided."""

    class A:
        pass

    def run_action(callback: Any, action: Any) -> str:
        return "run"

    ARCallReg.register_action(A, run_action=run_action)

    assert ARCallReg.get_callable(A(), "run_action") is run_action
    assert ARCallReg.get_callable(A(), "translate_action") is None


def test_get_callable_flag_returns_false_when_source_is_not_callable() -> None:
    """Test get_callable_flag returns False for non-callables."""

    assert ARCallReg.get_callable_flag("not_callable") is False


def test_get_callable_flag_returns_false_for_missing_name() -> None:
    """Test get_callable_flag returns False when the named entry is missing."""

    class A:
        pass

    assert ARCallReg.get_callable_flag(A(), "missing") is False


def test_unregister_rebuilds_flags_for_tuple_entries() -> None:
    """Test that unregister rebuilds flags and removes tuple-based entries."""

    class A:
        pass

    class B:
        pass

    def fetch_state_a(s: Any) -> str:
        return "state-a"

    def fetch_state_b(s: Any) -> str:
        return "state-b"

    ARCallReg.register(A, fetch_state=(fetch_state_a, True))
    ARCallReg.register(B, fetch_state=(fetch_state_b, False))

    assert ARCallReg.get_callable_flag(fetch_state_a) is True
    assert ARCallReg.get_callable_flag(fetch_state_b) is False

    ARCallReg.unregister(A)

    assert ARCallReg.get_callable_flag(fetch_state_a) is False
    assert ARCallReg.get_callable_flag(fetch_state_b) is False


def test_unregister_and_clear() -> None:
    """Test unregistering and clearing the registry."""

    class S:
        pass

    def fn(s: Any) -> str:
        return "ok"

    ARCallReg.register(S, fetch_state=fn)
    assert ARCallReg.get_callable(S(), "fetch_state") is fn

    ARCallReg.unregister(S)
    assert ARCallReg.get_callable(S(), "fetch_state") is None

    # re-register and then clear everything
    ARCallReg.register(S, fetch_state=fn)
    ARCallReg.clear()
    assert ARCallReg.get_callable(S(), "fetch_state") is None


def test_get_callable_returns_none_when_missing() -> None:
    """Test that get_callable returns None when no callable is found."""

    class X:
        pass

    assert ARCallReg.get_callable(X(), "nope") is None
    assert ARCallReg.get_all_for(X()) == {}


def test_concurrent_registers_are_thread_safe() -> None:
    """Test that concurrent registrations are thread-safe."""

    class Root:
        pass

    def make_fn(i: int) -> Callable[[Any], int]:
        """Create a function that returns the given integer."""

        def f(s: Any) -> int:
            """Return the given integer."""

            return i

        return f

    def worker(i: int) -> None:
        """Register a function in the ARCallableRegistry."""

        ARCallReg.register(Root, **{f"fn{i}": make_fn(i)})

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    all_map = ARCallReg.get_all_for(Root())
    # expect all registered names to be present
    for i in range(8):
        key = f"fn{i}"
        assert key in all_map
        assert callable(all_map[key])
