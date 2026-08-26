from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from dotenv import load_dotenv

BROWSER_USE_PRIVACY_OVERRIDES = {
    "PYTHON_DOTENV_DISABLED": "1",
    "ANONYMIZED_TELEMETRY": "false",
    "BROWSER_USE_CLOUD_SYNC": "false",
}


def load_local_runtime_environment(path: Path) -> bool:
    """Load an explicit local environment file without re-enabling browser-use discovery."""
    dotenv_disabled = os.environ.pop("PYTHON_DOTENV_DISABLED", None)
    try:
        return load_dotenv(path)
    finally:
        if dotenv_disabled is not None:
            os.environ["PYTHON_DOTENV_DISABLED"] = dotenv_disabled


def browser_use_privacy_environment(source: Mapping[str, str]) -> dict[str, str]:
    """Return an isolated browser-use environment with outbound telemetry disabled."""
    return {**source, **BROWSER_USE_PRIVACY_OVERRIDES}
