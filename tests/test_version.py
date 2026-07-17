"""Test version consistency."""

from __future__ import annotations

from pathlib import Path
import tomllib

from asusrouter.const import USER_AGENT, __version__

_PYPROJECT = Path(__file__).parent.parent / "pyproject.toml"


def _pyproject_version() -> str:
    """Read the version from pyproject.toml."""

    data = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def test_const_matches_pyproject() -> None:
    """Const version must match pyproject version (bump both together)."""

    assert __version__ == _pyproject_version()


def test_user_agent_embeds_version() -> None:
    """USER_AGENT must embed the current version."""

    assert __version__ in USER_AGENT
