"""Flags module."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Flag(dict):
    """Flag class.

    This is just a wrapper for a dict."""
