from __future__ import annotations

import re
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

import yaml
from pydantic import Field, model_validator

from browser_agent_evaluation.core.models import AcceptanceSpec, BrowserEvalModel, TaskPolicy

_WORKFLOW_ID = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")


class WorkflowStep(BrowserEvalModel):
    id: str = Field(min_length=3, max_length=64)
    instruction: str = Field(min_length=5, max_length=4_000)
    acceptance: AcceptanceSpec

    @model_validator(mode="after")
    def validate_step_id(self) -> WorkflowStep:
        if not _WORKFLOW_ID.fullmatch(self.id):
            raise ValueError("workflow step ID must be a lowercase safe identifier")
        return self


class WorkflowStepRequest(BrowserEvalModel):
    """Connector-visible step input; controller acceptance is deliberately omitted."""

    workflow_id: str
    step_id: str
    instruction: str
    policy: TaskPolicy


class WorkflowSpec(BrowserEvalModel):
    schema_version: Literal[1]
    id: str
    start_url: str
    policy: TaskPolicy
    steps: list[WorkflowStep] = Field(min_length=1, max_length=100)
    final_acceptance: AcceptanceSpec

    @model_validator(mode="after")
    def validate_identity_and_start_url(self) -> WorkflowSpec:
        if not _WORKFLOW_ID.fullmatch(self.id):
            raise ValueError("workflow ID must be a lowercase safe identifier")
        parsed = urlparse(self.start_url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("workflow start URL must use HTTPS and include a hostname")
        if parsed.hostname not in self.policy.allowed_domains:
            raise ValueError("workflow start URL hostname must be in the allowlist")
        if len({step.id for step in self.steps}) != len(self.steps):
            raise ValueError("workflow step IDs must be unique")
        return self

    def connector_step_request(self, step: WorkflowStep) -> WorkflowStepRequest:
        return WorkflowStepRequest(
            workflow_id=self.id,
            step_id=step.id,
            instruction=step.instruction,
            policy=self.policy,
        )


def load_workflow(path: Path) -> WorkflowSpec:
    """Load one strict YAML workflow before a connector or browser is created."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("workflow must be a YAML object")
    return WorkflowSpec.model_validate(raw)
