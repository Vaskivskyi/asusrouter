"""Cleaning tools for AsusRouter."""

from __future__ import annotations

from typing import Any


def clean_content(content: str) -> str:
    """Clean the content from useless data"""

    # Remove the first character if it is a BOM
    if content.startswith("\ufeff"):
        content = content[1:]

    # Return the cleaned content
    return content


def clean_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Clean a dict from useless data

    This method performs recursively (to all the nested dicts) the following operations:
    - Convert all values which are empty strings ('') to None"""

    # Go through the dict and clean it
    for key, value in data.items():
        # Check if the value is a dict
        if isinstance(value, dict):
            # Clean the dict
            data[key] = clean_dict(value)
            # Continue to the next value
            continue
        # Check if the value is a string and if it is empty
        if isinstance(value, str) and value == "":
            # Convert the value to None
            data[key] = None

    # Return the cleaned dict
    return data


def clean_dict_key_prefix(data: dict[str, Any], prefix: str) -> dict[str, Any]:
    """Clean dict keys from prefix and an underscore (prefix_).

    This method only cleans the keys, but cannot be used to clean nested dicts."""

    cleaned_dict: dict[str, Any] = {}

    # Go through the dict and clean it
    for key, value in data.items():
        # Check if the key starts with the prefix
        if key.startswith(f"{prefix}_"):
            # Remove the prefix and underscore
            new_key = key.replace(f"{prefix}_", "")
            # Add the new key to the dict
            cleaned_dict[new_key] = value

            continue
        cleaned_dict[key] = value

    # Return the cleaned dict
    return cleaned_dict


def clean_dict_key(data: dict[str, Any], keys: str | list[str]) -> dict[str, Any]:
    """Clean dict from the keys. This method can be used to clean nested dicts."""

    cleaned_dict: dict[str, Any] = {}

    # Check if the keys is a string
    if isinstance(keys, str):
        keys = [keys]

    # Go through the dict and clean it
    for key, value in data.items():
        # Check if the key is in the keys
        if key in keys:
            continue
        cleaned_dict[key] = (
            clean_dict_key(value, keys) if isinstance(value, dict) else value
        )

    # Return the cleaned dict
    return cleaned_dict
