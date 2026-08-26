from __future__ import annotations

import os
from pathlib import Path

import pytest

from browser_agent_evaluation.browser.environment import (
    browser_use_privacy_environment,
    load_local_runtime_environment,
)


def test_explicit_environment_loads_after_browser_use_disables_discovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    environment_path = tmp_path / ".env"
    environment_path.write_text("BROWSER_EVAL_TEST_SECRET=available\n", encoding="utf-8")
    monkeypatch.setattr(os, "environ", {"PYTHON_DOTENV_DISABLED": "1"})

    assert load_local_runtime_environment(environment_path)
    assert os.environ["BROWSER_EVAL_TEST_SECRET"] == "available"
    assert os.environ["PYTHON_DOTENV_DISABLED"] == "1"


def test_browser_use_environment_forces_telemetry_and_cloud_sync_off() -> None:
    environment = browser_use_privacy_environment(
        {
            "ANONYMIZED_TELEMETRY": "true",
            "BROWSER_USE_CLOUD_SYNC": "1",
            "UNCHANGED": "value",
        }
    )

    assert environment["PYTHON_DOTENV_DISABLED"] == "1"
    assert environment["ANONYMIZED_TELEMETRY"] == "false"
    assert environment["BROWSER_USE_CLOUD_SYNC"] == "false"
    assert environment["UNCHANGED"] == "value"


def test_browser_use_environment_does_not_mutate_caller_mapping() -> None:
    source = {"ANONYMIZED_TELEMETRY": "true"}

    browser_use_privacy_environment(source)

    assert source == {"ANONYMIZED_TELEMETRY": "true"}
