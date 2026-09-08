from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_TASK_ID = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")


class BrowserEvalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TaskPolicy(BrowserEvalModel):
    allowed_domains: list[str] = Field(min_length=1, max_length=8)
    risk: Literal["read_only", "synthetic_form"]
    allow_form_submit: bool = False
    allowed_submit_labels: list[str] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def validate_submit_policy(self) -> TaskPolicy:
        if self.risk == "read_only" and self.allow_form_submit:
            raise ValueError("read-only tasks cannot allow form submission")
        if self.allow_form_submit and self.allowed_submit_labels:
            raise ValueError("submit authority cannot mix generic and labeled submission")
        return self


class AcceptanceSpec(BrowserEvalModel):
    verifier: Literal["marca_article", "amazon_coffee_under_14"] | None = None
    page_title: str | None = Field(default=None, min_length=1, max_length=200)
    url_contains: str | None = Field(default=None, min_length=1, max_length=500)
    visible_text: str | None = Field(default=None, min_length=1, max_length=500)
    input_value: str | None = Field(default=None, min_length=1, max_length=500)

    @model_validator(mode="after")
    def require_assertion(self) -> AcceptanceSpec:
        if not any(
            (self.verifier, self.page_title, self.url_contains, self.visible_text, self.input_value)
        ):
            raise ValueError("acceptance requires at least one assertion")
        return self


class TaskSpec(BrowserEvalModel):
    schema_version: Literal[1]
    id: str
    start_url: str
    instruction: str = Field(min_length=10, max_length=4_000)
    completion: str = Field(min_length=5, max_length=1_000)
    policy: TaskPolicy
    max_actions: int = Field(ge=1, le=50)
    timeout_seconds: int = Field(ge=1, le=300)
    acceptance: AcceptanceSpec
    verification_mode: Literal["task_completion", "reachability"] = "task_completion"

    @model_validator(mode="after")
    def validate_identity_and_start_url(self) -> TaskSpec:
        if not _TASK_ID.fullmatch(self.id):
            raise ValueError("task id must be a lowercase safe identifier")
        parsed = urlparse(self.start_url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("start URL must use HTTPS and include a hostname")
        if parsed.hostname not in self.policy.allowed_domains:
            raise ValueError("start URL hostname must be in the allowlist")
        return self


class ActionTarget(BrowserEvalModel):
    role: str | None = Field(default=None, min_length=1, max_length=100)
    name: str | None = Field(default=None, min_length=1, max_length=300)
    text: str | None = Field(default=None, min_length=1, max_length=300)
    label: str | None = Field(default=None, min_length=1, max_length=300)
    placeholder: str | None = Field(default=None, min_length=1, max_length=300)

    @model_validator(mode="after")
    def require_semantic_locator(self) -> ActionTarget:
        if not any((self.role, self.name, self.text, self.label, self.placeholder)):
            raise ValueError("target requires a semantic locator")
        return self


class ExpectedState(BrowserEvalModel):
    kind: Literal["url_contains", "text_visible", "value_equals", "url_or_text_changes"]
    value: str = Field(default="", max_length=500)


class RestrictedBrowserAction(BrowserEvalModel):
    type: Literal["navigate", "click", "fill", "select", "check", "press", "wait", "extract_text"]
    target: ActionTarget | None = None
    value: str | None = Field(default=None, max_length=2_000)

    @model_validator(mode="after")
    def validate_action_shape(self) -> RestrictedBrowserAction:
        if self.type == "navigate":
            if not self.value:
                raise ValueError("navigate action requires a URL value")
            return self
        if self.type == "wait":
            if self.target is not None:
                raise ValueError("wait action does not accept a target")
            return self
        if self.target is None:
            raise ValueError(f"{self.type} action requires a target")
        if self.type in {"fill", "select", "press"} and not self.value:
            raise ValueError(f"{self.type} action requires a value")
        return self


class BrowserActionProposal(BrowserEvalModel):
    result: str | None = Field(default=None, max_length=4000)
    step_index: int = Field(ge=1, le=100)
    step_status: Literal["in_progress", "complete", "blocked"]
    action: RestrictedBrowserAction | None = None
    expected_state: ExpectedState | None = None

    @field_validator("result", mode="before")
    @classmethod
    def serialize_result_object(cls, value: object) -> object:
        return json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else value

    @model_validator(mode="after")
    def validate_status(self) -> BrowserActionProposal:
        if self.step_status == "in_progress" and self.action is None:
            raise ValueError("in-progress proposal requires an action")
        if self.step_status != "in_progress" and self.action is not None:
            raise ValueError("terminal proposal cannot include an action")
        return self


class UsageEvidence(BrowserEvalModel):
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    request_count: int = Field(ge=0)
    cost_usd: float | None = Field(default=None, ge=0)
    unavailable_reason: str | None = Field(default=None, min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_availability(self) -> UsageEvidence:
        usage_values = (self.prompt_tokens, self.completion_tokens, self.cost_usd)
        has_tokens = self.prompt_tokens is not None or self.completion_tokens is not None
        has_usage = any(value is not None for value in usage_values)
        if not has_usage and not self.unavailable_reason:
            raise ValueError("missing usage requires an unavailable reason")
        if has_tokens and self.cost_usd is None and not self.unavailable_reason:
            raise ValueError("token-only usage requires a cost-unavailable reason")
        if self.cost_usd is not None and self.unavailable_reason:
            raise ValueError("cost-available usage cannot include an unavailable reason")
        return self


RunnerName = Literal[
    "playwright_reference", "browser_use", "stagehand", "playwright_mcp", "restricted"
]
TrialOutcome = Literal[
    "passed", "unverified", "failed", "invalidated", "timed_out", "policy_denied"
]


class RunnerInput(BrowserEvalModel):
    runner: RunnerName
    prompt: str = Field(min_length=1)


class TrialEvidence(BrowserEvalModel):
    verification_evidence: dict[str, str] = Field(default_factory=dict)
    schema_version: Literal[1] = 1
    trial_id: str
    task_id: str
    runner: RunnerName
    model_id: str | None = Field(default=None, min_length=1, max_length=200)
    started_at: datetime
    ended_at: datetime
    outcome: TrialOutcome
    duration_ms: int = Field(ge=0)
    action_count: int = Field(ge=0)
    retry_count: int = Field(ge=0)
    cleanup_verified: bool
    assertion_results: dict[str, bool] = Field(default_factory=dict)
    invalidation_reason: str | None = Field(default=None, max_length=500)
    policy_events: list[str] = Field(default_factory=list, max_length=50)
    observation_mode: Literal[
        "accessibility_dom", "framework_owned", "mcp_accessibility", "reference"
    ]
    usage: UsageEvidence

    @model_validator(mode="after")
    def validate_outcome(self) -> TrialEvidence:
        if self.ended_at < self.started_at:
            raise ValueError("trial cannot end before it starts")
        if self.outcome == "invalidated" and not self.invalidation_reason:
            raise ValueError("invalidated trial requires a reason")
        if self.outcome != "invalidated" and self.invalidation_reason:
            raise ValueError("only invalidated trials may include an invalidation reason")
        if self.outcome in {"passed", "unverified"} and (
            not self.assertion_results or not all(self.assertion_results.values())
        ):
            raise ValueError("accepted or reached trials require successful independent assertions")
        return self


def acceptance_outcome(task: TaskSpec, *, accepted: bool) -> TrialOutcome:
    if not accepted:
        return "failed"
    if task.verification_mode == "reachability":
        return "unverified"
    return "passed"


def render_runner_instruction(task: TaskSpec) -> str:
    domains = ", ".join(task.policy.allowed_domains)
    return (
        "Complete this browser task exactly as written. Verify progress after each step. "
        "Do not log in, download files, bypass CAPTCHAs, use a personal browser, or leave "
        f"the allowed domains: {domains}.\n\n"
        f"Steps:\n{task.instruction}\n\n"
        f"Completion: {task.completion}\n"
        f"Action limit: {task.max_actions}. Timeout: {task.timeout_seconds} seconds."
    )


def create_runner_input(task: TaskSpec, *, runner: RunnerName) -> RunnerInput:
    return RunnerInput(runner=runner, prompt=render_runner_instruction(task))


def now_utc() -> datetime:
    return datetime.now(UTC)
