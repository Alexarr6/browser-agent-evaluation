from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from browser_agent_evaluation.core.models import BrowserEvalModel

AiRunnerName = Literal["restricted", "browser_use", "playwright_mcp"]
TaskCategory = Literal["standard", "experimental"]


class ManifestTask(BrowserEvalModel):
    id: str = Field(min_length=1, max_length=100)
    category: TaskCategory
    source: str = Field(min_length=1, max_length=500)
    contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    max_actions: int = Field(ge=1)
    timeout_seconds: int = Field(ge=1)
    acceptance_fields: list[str] = Field(min_length=1)


class ManifestLimits(BrowserEvalModel):
    max_total_usd_per_round: float | None = Field(default=None, gt=0)
    max_trial_usd: float | None = Field(default=None, gt=0)
    max_requests_per_trial: int = Field(ge=1)
    max_tokens_per_trial: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_cost_limits(self) -> ManifestLimits:
        if (self.max_total_usd_per_round is None) != (self.max_trial_usd is None):
            raise ValueError("manifest cost limits must both be set or both be omitted")
        return self


class EvaluationManifest(BrowserEvalModel):
    schema_version: Literal[1] = 1
    created_at: datetime
    task_language: Literal["es", "en"]
    tasks: list[ManifestTask] = Field(min_length=1)
    ai_runners: list[AiRunnerName] = Field(min_length=1)
    repetitions: int = Field(ge=1)
    round_indices: list[int] = Field(min_length=1)
    round_seeds: list[int] = Field(min_length=1)
    model: str = Field(min_length=1, max_length=200)
    provider_endpoint: str = Field(min_length=8, max_length=500)
    reference_browser_version: str | None = Field(default=None, max_length=200)
    browser_use_browser_version: str | None = Field(default=None, max_length=200)
    rendering_profile: Literal["strict", "visual-parity"]
    headless: bool
    skip_ai_on_reference_failure: bool
    limits: ManifestLimits
    artifact_files: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_complete_manifest(self) -> EvaluationManifest:
        if len(self.round_indices) != self.repetitions:
            raise ValueError("manifest round count must match repetitions")
        if len(self.round_seeds) != self.repetitions:
            raise ValueError("manifest seed count must match repetitions")
        if len(set(self.round_indices)) != len(self.round_indices):
            raise ValueError("manifest round indices must be unique")
        if len({task.id for task in self.tasks}) != len(self.tasks):
            raise ValueError("manifest task IDs must be unique")
        if len(set(self.ai_runners)) != len(self.ai_runners):
            raise ValueError("manifest AI runners must be unique")
        if len(set(self.artifact_files)) != len(self.artifact_files):
            raise ValueError("manifest artifact files must be unique")
        unsafe_files = (
            Path(name).name != name or not name.endswith(".json")
            for name in self.artifact_files
        )
        if any(unsafe_files):
            raise ValueError("manifest artifact files must be local JSON filenames")
        return self


def manifest_task(
    *,
    task_id: str,
    category: TaskCategory,
    source: Path,
    max_actions: int,
    timeout_seconds: int,
    acceptance_fields: list[str],
) -> ManifestTask:
    return ManifestTask(
        id=task_id,
        category=category,
        source=source.name,
        contract_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        max_actions=max_actions,
        timeout_seconds=timeout_seconds,
        acceptance_fields=acceptance_fields,
    )


def write_evaluation_manifest(manifest: EvaluationManifest, *, output_dir: Path) -> Path:
    path = output_dir / "run-manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def load_evaluation_manifest(path: Path) -> EvaluationManifest:
    return EvaluationManifest.model_validate_json(path.read_bytes())
