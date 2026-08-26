from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field, field_validator, model_validator

from browser_agent_evaluation.models import BrowserEvalModel

_ENVIRONMENT_NAME = re.compile(r"^[A-Z][A-Z0-9_]{1,127}$")
_MODEL_ID = re.compile(r"^[a-z0-9][a-z0-9._/-]{2,199}$")
_ENVIRONMENT_REFERENCE = re.compile(
    r"^\$\{([A-Z][A-Z0-9_]{1,127})(?::-([^}]+))?\}$"
)


class BrowserConfiguration(BrowserEvalModel):
    executable_path_env: str = Field(min_length=2, max_length=128)
    browser_use_executable_path_env: str = Field(min_length=2, max_length=128)
    headless: bool = True
    fresh_profile: bool = True

    @field_validator("executable_path_env", "browser_use_executable_path_env")
    @classmethod
    def validate_environment_name(cls, value: str) -> str:
        if not _ENVIRONMENT_NAME.fullmatch(value):
            raise ValueError("browser executable environment variable is invalid")
        return value

    @model_validator(mode="after")
    def require_fresh_profile(self) -> BrowserConfiguration:
        if not self.fresh_profile:
            raise ValueError("experiment browser requires a fresh profile")
        return self


class ProviderConfiguration(BrowserEvalModel):
    endpoint: str = Field(min_length=8, max_length=500)
    api_key_env: str = Field(min_length=2, max_length=128)

    @field_validator("endpoint")
    @classmethod
    def require_https_endpoint(cls, value: str) -> str:
        if not value.startswith("https://"):
            raise ValueError("provider endpoint must use HTTPS")
        return value.rstrip("/")

    @field_validator("api_key_env")
    @classmethod
    def validate_environment_name(cls, value: str) -> str:
        if not _ENVIRONMENT_NAME.fullmatch(value):
            raise ValueError("provider API-key environment variable is invalid")
        return value


class BudgetConfiguration(BrowserEvalModel):
    max_total_usd: float | None = Field(default=None, gt=0)
    max_run_usd: float | None = Field(default=None, gt=0)
    max_tokens_per_run: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_cost_budget(self) -> BudgetConfiguration:
        if (self.max_total_usd is None) != (self.max_run_usd is None):
            raise ValueError("cost caps must be configured together or both omitted")
        if (
            self.max_total_usd is not None
            and self.max_run_usd is not None
            and self.max_run_usd > self.max_total_usd
        ):
            raise ValueError("per-run cost cap cannot exceed total cost cap")
        return self


class ModelRunnerConfiguration(BrowserEvalModel):
    enabled: bool = True
    model: str = "openai/gpt-5.6-luna"

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str) -> str:
        if not _MODEL_ID.fullmatch(value):
            raise ValueError("runner model ID is invalid")
        return value


class BrowserUseConfiguration(ModelRunnerConfiguration):
    completion_tokens: int | None = Field(default=None, ge=1)


class ExperimentRunners(BrowserEvalModel):
    playwright_reference: bool = True
    restricted: ModelRunnerConfiguration = Field(default_factory=ModelRunnerConfiguration)
    browser_use: BrowserUseConfiguration = Field(default_factory=BrowserUseConfiguration)
    playwright_mcp: ModelRunnerConfiguration = Field(default_factory=ModelRunnerConfiguration)


class ExecutionConfiguration(BrowserEvalModel):
    repetitions: int = Field(default=3, ge=1)
    seed: int = 20260824
    task_language: Literal["es", "en"] = "en"
    max_requests_per_run: int = Field(default=48, ge=1)


class WorkflowLocation(BrowserEvalModel):
    directory: str = Field(min_length=1, max_length=500)


class ReportLocation(BrowserEvalModel):
    directory: str = Field(min_length=1, max_length=500)


class ExperimentConfiguration(BrowserEvalModel):
    schema_version: Literal[1]
    browser: BrowserConfiguration
    provider: ProviderConfiguration
    budget: BudgetConfiguration
    runners: ExperimentRunners = Field(default_factory=ExperimentRunners)
    execution: ExecutionConfiguration = Field(default_factory=ExecutionConfiguration)
    workflows: WorkflowLocation
    reports: ReportLocation

    @property
    def enabled_runner_ids(self) -> tuple[str, ...]:
        runners = self.runners
        selected: list[str] = []
        if runners.playwright_reference:
            selected.append("playwright_reference")
        for runner_id in ("restricted", "browser_use", "playwright_mcp"):
            if getattr(runners, runner_id).enabled:
                selected.append(runner_id)
        return tuple(selected)

    @model_validator(mode="after")
    def require_one_common_model_for_enabled_ai_runners(self) -> ExperimentConfiguration:
        enabled_models = {
            configuration.model
            for configuration in (
                self.runners.restricted,
                self.runners.browser_use,
                self.runners.playwright_mcp,
            )
            if configuration.enabled
        }
        if len(enabled_models) > 1:
            raise ValueError("enabled AI runners must use the same model for comparison")
        return self


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
