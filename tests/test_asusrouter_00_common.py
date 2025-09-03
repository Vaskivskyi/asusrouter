"""Tests for the asusrouter module / Common parts."""

from asusrouter.asusrouter import AsusRouter

hostname = "192.168.1.1"
username = "admin"
password = "password"


def get_asusrouter_instance() -> AsusRouter:
    """Get a new instance of the AsusRouter."""

    return AsusRouter(
        hostname=hostname,
        username=username,
        password=password,
    )
