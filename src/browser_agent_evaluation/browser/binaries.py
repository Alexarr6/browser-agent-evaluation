from __future__ import annotations

import os
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

MCP_ACTION_TIMEOUT_SECONDS = 60
MCP_NAVIGATION_TIMEOUT_SECONDS = 90
