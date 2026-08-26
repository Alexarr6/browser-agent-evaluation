from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from browser_agent_evaluation.models import BrowserEvalModel, UsageEvidence


class Provenance(BrowserEvalModel):
    connector_id: str = Field(min_length=1, max_length=100)
    model_id: str | None = Field(default=None, min_length=1, max_length=200)
    configuration_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class StepReceipt(BrowserEvalModel):
    schema_version: Literal[1] = 1
    run_id: str = Field(min_length=1, max_length=100)
    workflow_id: str = Field(min_length=1, max_length=64)
    step_id: str = Field(min_length=1, max_length=64)
    started_at: datetime
    ended_at: datetime
    provenance: Provenance
    action_summary: list[str] = Field(default_factory=list, max_length=100)
    usage: UsageEvidence
    acceptance: dict[str, bool]
    outcome: Literal["passed", "failed"]
    diagnostic: str | None = Field(default=None, max_length=2_000)


class RunReceipt(BrowserEvalModel):
    schema_version: Literal[1] = 1
    run_id: str = Field(min_length=1, max_length=100)
    workflow_id: str = Field(min_length=1, max_length=64)
    provenance: Provenance
    step_receipts: list[StepReceipt] = Field(default_factory=list)
    final_acceptance: dict[str, bool] = Field(default_factory=dict)
    outcome: Literal["passed", "failed", "unsupported", "invalidated"]
    cleanup_verified: bool
    cleanup_detail: str | None = Field(default=None, max_length=2_000)
