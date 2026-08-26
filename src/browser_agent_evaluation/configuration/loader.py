from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

import yaml

from browser_agent_evaluation.configuration.models import ExperimentConfiguration

_ENVIRONMENT_REFERENCE = re.compile(
    r"^\$\{([A-Z][A-Z0-9_]{1,127})(?::-([^}]+))?\}$"
)


def load_experiment_configuration(path: Path) -> ExperimentConfiguration:
    """Load one strict, repository-local experiment configuration document."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("experiment configuration must be a YAML object")
    return ExperimentConfiguration.model_validate(_resolve_environment_references(raw))


def _resolve_environment_references(value: object) -> object:
    if isinstance(value, dict):
        return {key: _resolve_environment_references(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_environment_references(item) for item in value]
    if not isinstance(value, str):
        return value
    match = _ENVIRONMENT_REFERENCE.fullmatch(value)
    if match is None:
        return value
    variable, default = match.groups()
    resolved = os.environ.get(variable, default)
    if not resolved:
        raise ValueError(f"required environment variable is unset: {variable}")
    return resolved


def configuration_sha256(configuration: ExperimentConfiguration) -> str:
    """Return the canonical hash persisted with every future runtime receipt."""
    canonical = json.dumps(
        configuration.model_dump(mode="json"),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
