from __future__ import annotations

import os
import subprocess
from pathlib import Path


def configured_executable(environment_name: str) -> Path:
    value = os.environ.get(environment_name)
    if not value:
        raise RuntimeError(
            f"{environment_name} is required; copy runtime.env.example and set the executable path"
        )
    executable = Path(value).expanduser()
    if not executable.is_file():
        raise RuntimeError(f"{environment_name} does not point to a file: {executable}")
    return executable


def executable_version(executable: Path) -> str | None:
    """Return a browser's self-reported version without exposing its local path."""
    try:
        result = subprocess.run(
            [str(executable), "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    version = result.stdout.strip() or result.stderr.strip()
    return version if result.returncode == 0 and version else None


MCP_ACTION_TIMEOUT_SECONDS = 60
MCP_NAVIGATION_TIMEOUT_SECONDS = 90
