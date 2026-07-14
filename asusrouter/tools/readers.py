"""Reading tools for AsusRouter."""

from __future__ import annotations

import ast
import json
import logging
import re
from typing import Any

from asusrouter.tools.converters_v2.raw import (
    raw_to_bool,
    raw_to_float,
    raw_to_str,
)
from asusrouter.tools.types import ARCallableType
from asusrouter.tools.units import (
    DataRateUnitConverter,
    UnitConverterBase,
    UnitOfDataRate,
)

_LOGGER = logging.getLogger(__name__)


# Random symbols to avoid json errors
RANDOM_SYMBOLS: list[str] = [
    "\u0000",
    "\u0001",
    "\u0002",
    "\u0003",
    "\u0004",
    "\u0005",
    "\u0006",
    "\u0007",
    "\u0008",
    "\u0009",
]


def is_non_negative(value: Any) -> bool:
    """Check if the value is non-negative."""

    return (raw_to_float(value) or 0.0) >= 0


def is_true_in_dict(value: str, data: dict[str, Any]) -> bool:
    """Check if the value exists in the dict and is equal to 1."""

    return raw_to_bool(data.get(value)) is True


def read_js_variables(content: str, **kwargs: Any) -> dict[str, Any]:
    """Get all the JS variables from the content."""

    content = raw_to_str(content) or ""
    # Create a dict to store the data
    js_variables: dict[str, Any] = {}

    # regex = re.compile(r"(\w+)\s*=\s*(.*?);$", re.DOTALL | re.MULTILINE)
    regex = re.compile(
        r"""(?m)                    # multiline mode
        \b                          # word boundary before variable name
        (\w+)\s*=\s*                # variable name and assignment
        (
            (?:
                "(?:[^"\\]|\\.)*"   # double-quoted string
                | '(?:[^'\\]|\\.)*' # single-quoted string
                | [^;]*?            # or anything up to semicolon
            )
        )
        \s*;                        # semicolon ends the assignment
        """,
        re.VERBOSE,
    )

    for match in regex.finditer(content):
        key, value = match.groups()

        # Clean value from the array indexes
        value = re.sub(r"\[\d+\]", "", value)

        # Try JSON
        try:
            js_variables[key] = json.loads(value.encode().decode("utf-8-sig"))
            continue
        except json.JSONDecodeError:
            pass
        try:
            # Try python literal eval
            js_variables[key] = ast.literal_eval(value)
            continue
        except (ValueError, SyntaxError):
            pass
        # Clean the value of quotes if it starts and ends with them
        if (value.startswith("'") and value.endswith("'")) or (
            value.startswith('"') and value.endswith('"')
        ):
            value = value[1:-1]
        js_variables[key] = value

    # Return the JS variables
    return js_variables


def read_json_content(content: str | None, **kwargs: Any) -> dict[str, Any]:
    """Get the json content."""

    content = raw_to_str(content)
    if not content:
        return {}

    # Random control characters to avoid json errors
    for symbol in RANDOM_SYMBOLS:
        content = content.replace(symbol, "")

    # Handle missing values in JSON
    content = re.sub(r"\s*,\s*,", ", ", content)
    content = re.sub(r"^\s*{\s*,", "{", content)
    content = re.sub(r",\s*}\s*$", "}", content)

    # Handle keys without values
    content = re.sub(r":\s*(,|\})", ": null\\1", content)

    # Return the json content
    try:
        json_data = json.loads(content.encode().decode("utf-8-sig"))
        if isinstance(json_data, dict):
            return json_data
        return {}
    except json.JSONDecodeError as ex:
        _LOGGER.error(
            "Unable to decode json content with exception `%s`.\
                Please, copy this and fill in a bug report: %s",
            ex,
            content,
        )
        return {}


def read_units_as_base(
    converter: type[UnitConverterBase],
    units: Any,
    check_calls: ARCallableType | list[ARCallableType] | None = None,
    fallback_value: float = 0.0,
) -> ARCallableType:
    """Create a reader from the units to the base."""

    if not isinstance(converter, type) or not issubclass(
        converter, UnitConverterBase
    ):
        raise TypeError("Converter must be a subclass of UnitConverterBase")

    # Convert single check call to a list
    if check_calls is not None and not isinstance(check_calls, list):
        check_calls = [check_calls]

    def reader(value: Any) -> float:
        """Read the value as a base unit."""

        # Use the converter with explicit None on unsupported types
        fval = raw_to_float(value)

        # Convert to base if all the checks passed
        if isinstance(fval, float) and (
            check_calls is None or all(call(fval) for call in check_calls)
        ):
            return converter.convert_to_base(fval, units)

        return fallback_value

    return reader


def read_units_data_rate(units: UnitOfDataRate) -> ARCallableType:
    """Read data rate values from the specified unit type."""

    return read_units_as_base(
        DataRateUnitConverter, units, is_non_negative, 0.0
    )
