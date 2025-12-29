"""Bump version tool for AsusRouter."""

from pathlib import Path
import re
import shutil
import subprocess
import sys


def update_const_py(
    const_path: Path, major: int, minor: int, patch: str
) -> None:
    """Update the const.py file with the new version."""

    text = const_path.read_text(encoding="utf-8")
    orig_text = text
    text, n1 = re.subn(
        r"MAJOR_VERSION: Final\[int\] = \d+",
        f"MAJOR_VERSION: Final[int] = {major}",
        text,
    )
    text, n2 = re.subn(
        r"MINOR_VERSION: Final\[int\] = \d+",
        f"MINOR_VERSION: Final[int] = {minor}",
        text,
    )
    text, n3 = re.subn(
        r'PATCH_VERSION: Final\[str\] = "[^"]+"',
        f'PATCH_VERSION: Final[str] = "{patch}"',
        text,
    )

    if text != orig_text:
        const_path.write_text(text, encoding="utf-8")


def update_pyproject(
    pyproject_path: Path, major: int, minor: int, patch: str
) -> None:
    """Update the pyproject.toml file with the new version."""

    text = pyproject_path.read_text(encoding="utf-8")
    orig_text = text
    text, n = re.subn(
        r'^(\s*version\s*=\s*)"[0-9a-zA-Z\.\-]+"',
        rf'\1"{major}.{minor}.{patch}"',
        text,
        flags=re.MULTILINE,
    )
    if n == 0:
        print("Warning: version field not found in pyproject.toml.")  # noqa: T201
    if text != orig_text:
        pyproject_path.write_text(text, encoding="utf-8")


def sync_uv_lock() -> None:
    """Sync uv.lock file after version bump."""

    try:
        uv_path = shutil.which("uv")
        if uv_path is None:
            print("Warning: uv executable not found in PATH.")  # noqa: T201
            return
        subprocess.run([uv_path, "sync"], check=True)  # noqa: S603
        print("uv.lock synced successfully.")  # noqa: T201
    except Exception as e:  # noqa: BLE001
        print(f"Failed to sync uv.lock: {e}")  # noqa: T201


def main() -> None:
    """Bump version."""

    if len(sys.argv) != 4:  # noqa: PLR2004
        print("Usage: python tools/bump_version.py <MAJOR> <MINOR> <PATCH>")  # noqa: T201
        sys.exit(1)

    major, minor, patch = sys.argv[1:4]

    root = Path(__file__).parent.parent
    const_py = root / "asusrouter" / "const.py"
    pyproject = root / "pyproject.toml"
    update_const_py(const_py, int(major), int(minor), patch)
    update_pyproject(pyproject, int(major), int(minor), patch)
    print(f"Bumped version to {major}.{minor}.{patch}")  # noqa: T201

    sync_uv_lock()


if __name__ == "__main__":
    main()
