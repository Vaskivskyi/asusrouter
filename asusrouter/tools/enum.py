"""Enum utilities."""

from __future__ import annotations

from typing import Any, Self, cast

from asusrouter.tools.converters import clean_string, safe_int


class FromIntMixin:
    """Mixin providing a `from_value` classmethod for int-based enums.

    Any enum inheriting from this mixin have to define an `UNKNOWN` member.
    """

    @classmethod
    def from_value(cls, value: Any) -> Self:
        """Resolve an enum member."""

        # If already an enum member, return it
        if isinstance(value, cls):
            return value

        # Try integer conversion first
        vint = safe_int(value)
        if vint is not None:
            try:
                return cls(vint)  # type: ignore[call-arg]
            except ValueError:
                pass

        # Try key names
        vstr = clean_string(value)
        if isinstance(vstr, str):
            member = getattr(cls, vstr.upper(), None)
            if member is not None:
                return cast(Self, member)

        # Fallback to UNKNOWN member if defined on the enum class
        unknown = getattr(cls, "UNKNOWN", None)
        if unknown is not None:
            return cast(Self, unknown)

        raise ValueError(
            f"{cls.__name__}.from_value: cannot resolve {value!r} "
            "and no `UNKNOWN` member is defined"
        )


class FromStrMixin:
    """Mixin providing a `from_value` classmethod for string-based enums.

    Any enum inheriting from this mixin have to define an `UNKNOWN` member.
    """

    @classmethod
    def from_value(cls, value: Any) -> Self:
        """Resolve an enum member from a string value."""

        # If already an enum member, return it
        if isinstance(value, cls):
            return value

        vstr = clean_string(value)
        if isinstance(vstr, str):
            # Check whether this is a value
            value_map = getattr(cls, "_value2member_map_", {})
            member = value_map.get(vstr)
            if member is not None:
                return cast(Self, member)

            # Check if a key exists
            member = getattr(cls, vstr.upper(), None)
            if member is not None:
                return cast(Self, member)

        # Fallback to UNKNOWN member if defined on the enum class
        unknown = getattr(cls, "UNKNOWN", None)
        if unknown is not None:
            return cast(Self, unknown)

        raise ValueError(
            f"{cls.__name__}.from_value: cannot resolve {value!r} "
            "and no `UNKNOWN` member is defined"
        )
