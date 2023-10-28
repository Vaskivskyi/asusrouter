"""Attributes module for AsusRouter."""

from enum import Enum


class AsusRouterAttribute(str, Enum):
    """Attributes enum."""

    MAC = "mac"
    WLAN_LIST = "wlan_list"
