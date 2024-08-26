"""Reading tools for AsusRouter"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from asusrouter.const import ContentType
from asusrouter.tools.converters import clean_input

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


def merge_dicts(
    data: dict[Any, Any], merge_data: dict[Any, Any]
) -> dict[Any, Any]:
    """This methods merges two nested dicts into a single one
    while keeping all the existing values"""

    # Create a new dictionary to store the merged data
    merged_data = data.copy()

    # Go through the merge data and fill the merged data
    for key, value in merge_data.items():
        # Check if the value is a dict
        if isinstance(value, dict):
            # Check if the key is in the merged data
            if key not in merged_data or merged_data[key] is None:
                # Add the key to the merged data
                merged_data[key] = {}
            # Merge the dicts
            merged_data[key] = merge_dicts(merged_data[key], value)
            # Continue to the next value
            continue
        # Check if the key is in the merged data
        if key not in merged_data:
            # Add the key to the merged data
            merged_data[key] = value
        else:
            # If the key is already in the merged data, compare the values
            if merged_data[key] is None:
                # If the value in the merged data is None, take the value from the merge data
                merged_data[key] = value
            elif value is None:
                # If the value in the merge data is not None
                # and the value in the merge data is None, keep the value in the merged data
                pass
            else:
                # If both values are not None, keep the value from the merged data
                pass

    # Return the merged data
    return merged_data


def read_as_snake_case(data: str) -> str:
    """Convert a string to snake case"""

    string = (
        re.sub(r"(?<=[a-z])(?=[A-Z])|[^a-zA-Z]", " ", data)
        .strip()
        .replace(" ", "_")
    )
    result = "".join(string.lower())
    while "__" in result:
        result = result.replace("__", "_")

    return result


def read_content_type(headers: dict[str, str]) -> ContentType:
    """Get the content type from the headers"""

    # Get the content type from the headers
    content_type = headers.get("content-type", "").split(";")[0].strip()
    # Find the content type in ContentType enum and return correct ContentType enum
    for content_type_enum in ContentType:
        if content_type_enum.value == content_type:
            return content_type_enum

    # If the content type is not found, return the content type as text
    return ContentType.UNKNOWN


@clean_input
def read_js_variables(content: str) -> dict[str, Any]:
    """Get all the JS variables from the content"""

    # Create a dict to store the data
    js_variables: dict[str, Any] = {}

    # Split the content into lines, strip them, remove the last semicolon
    lines = content.splitlines()
    lines = [line.strip() for line in lines]
    lines = [line[:-1] if line.endswith(";") else line for line in lines]

    # Create a regex to match the data. Consider the following:
    # The key is a string which can contain letters, numbers, underscores
    # The key and the value are separated by an equal sign (surrounded by spaces or not)
    regex = re.compile(r"(\w+)\s*=\s*(.*)")

    # Go through the lines and fill the match data to the dict
    for line in lines:
        match = regex.match(line)
        if match:
            key, value = match.groups()
            # Clean the value of quotes if it starts and ends with them
            if (value.startswith("'") and value.endswith("'")) or (
                value.startswith('"') and value.endswith('"')
            ):
                value = value[1:-1]
            js_variables[key] = value

    # Return the JS variables
    return js_variables


@clean_input
def read_json_content(content: Optional[str]) -> dict[str, Any]:
    """Get the json content"""

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
        return json.loads(content.encode().decode("utf-8-sig"))
    except json.JSONDecodeError as ex:
        _LOGGER.error(
            "Unable to decode json content with exception `%s`.\
                Please, copy this and fill in a bug report: %s",
            ex,
            content,
        )
        return {}


@clean_input
def readable_mac(raw: Optional[str]) -> bool:
    """Checks if string is MAC address"""

    if isinstance(raw, str):
        if re.search(
            re.compile("^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$"), raw
        ):
            return True

    return False
