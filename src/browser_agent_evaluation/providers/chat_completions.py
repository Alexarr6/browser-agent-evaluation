from __future__ import annotations

import json
from dataclasses import dataclass

import httpx

from browser_agent_evaluation.core.budget import ModelBudget
from browser_agent_evaluation.core.models import (
    BrowserActionProposal,
    ExpectedState,
    TaskSpec,
    UsageEvidence,
    render_runner_instruction,
)
from browser_agent_evaluation.core.pricing import provider_cost_or_model_estimate

DEFAULT_MODEL = "gpt-5.6-luna"


class ProviderContractError(RuntimeError):
    """Raised when an adapter cannot participate in a comparable model trial."""


@dataclass(frozen=True)
class ProviderConfiguration:
    provider: str
    model: str
    endpoint: str

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ProviderContractError("provider identity is required")
        if not self.model.strip():
            raise ProviderContractError("provider model is required")
        if not self.endpoint.startswith("https://"):
            raise ProviderContractError("provider endpoint must use HTTPS")


def require_comparable_usage(usage: UsageEvidence) -> None:
    if usage.prompt_tokens is None or usage.completion_tokens is None:
        raise ProviderContractError("comparable usage requires provider-reported tokens")


class ChatCompletionsPlanner:
    """Bounded JSON-only restricted-agent planner using the approved endpoint."""

    def __init__(
        self,
        *,
        api_key: str,
        budget: ModelBudget,
        trial_id: str,
        client: httpx.AsyncClient,
        endpoint: str,
        model: str = DEFAULT_MODEL,
        max_completion_tokens: int | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("provider API key is required")
        self._api_key = api_key
        self._budget = budget
        self._trial_id = trial_id
        self._client = client
        self._model = model
        self._endpoint = endpoint.rstrip("/")
        self._max_completion_tokens = max_completion_tokens
        self._prompt_tokens = 0
        self._completion_tokens = 0
        self._cost_usd: float | None = 0.0
        self._request_count = 0

    @property
    def usage(self) -> UsageEvidence:
        return UsageEvidence(
            prompt_tokens=self._prompt_tokens,
            completion_tokens=self._completion_tokens,
            request_count=self._request_count,
            cost_usd=self._cost_usd,
            unavailable_reason=(
                "configured provider does not report per-request USD cost"
                if self._cost_usd is None
                else None
            ),
        )

    async def propose(
        self,
        *,
        task: TaskSpec,
        observation: str,
        action_history: tuple[str, ...],
        remaining_actions: int,
    ) -> BrowserActionProposal:
        self._budget.before_request(self._trial_id)
        action_schema = json.dumps(BrowserActionProposal.model_json_schema())
        planner_contract = (
            "Return exactly one JSON object that validates against this schema: "
            + action_schema
            + ". Never return Markdown, JavaScript, arbitrary selectors, credentials, "
            "or actions outside the task. Use only semantic targets (role, name, label, "
            "placeholder, or visible text). Prefer role plus name; use a role-only target "
            "only when the page has one matching control. The supported actions are "
            "navigate, click, fill, select, check, press, wait, and extract_text. For "
            "select, value may be either the option's visible label or its HTML value. "
            "For wait, omit target. For Enter on a search control, preserve its accessible "
            "name or placeholder so the task policy can authorize it."
        )
        request_payload: dict[str, object] = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": planner_contract,
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "task": render_runner_instruction(task),
                            "observation": observation[:8_000],
                            "action_history": action_history,
                            "remaining_actions": remaining_actions,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "response_format": {"type": "json_object"},
        }
        if self._max_completion_tokens is not None:
            request_payload["max_completion_tokens"] = self._max_completion_tokens
        response = await self._client.post(
            f"{self._endpoint}/chat/completions",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json=request_payload,
            timeout=120,
        )
        if response.is_error:
            raise ProviderContractError(
                f"provider returned HTTP {response.status_code}: {_safe_error_detail(response)}"
            )
        payload = response.json()
        usage = payload.get("usage", {})
        if not isinstance(usage, dict):
            raise ProviderContractError("provider response lacks usage")
        prompt_tokens = _required_int(usage, "prompt_tokens")
        completion_tokens = _required_int(usage, "completion_tokens")
        cost = provider_cost_or_model_estimate(usage, model=self._model)
        self._budget.consume_usage(self._trial_id, cost, prompt_tokens, completion_tokens)
        self._prompt_tokens += prompt_tokens
        self._completion_tokens += completion_tokens
        self._cost_usd = None if cost is None or self._cost_usd is None else self._cost_usd + cost
        self._request_count += 1
        try:
            content = payload["choices"][0]["message"]["content"]
        except (IndexError, KeyError, TypeError) as error:
            raise ProviderContractError("provider response lacks a planner message") from error
        return parse_planner_proposal(content, step_index=task.max_actions - remaining_actions + 1)


def parse_planner_proposal(content: str, *, step_index: int) -> BrowserActionProposal:
    try:
        return BrowserActionProposal.model_validate_json(content)
    except ValueError:
        pass
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as error:
        raise ProviderContractError("provider planner response violates action schema") from error
    if not isinstance(payload, dict):
        raise ProviderContractError("provider planner response violates action schema")
    try:
        expected_state = None
        action_payload = dict(payload)
        if "expected_state" in action_payload:
            raw_expected_state = action_payload.pop("expected_state")
            if not isinstance(raw_expected_state, dict):
                raise ValueError("expected_state must be an object")
            expected_state = ExpectedState.model_validate(raw_expected_state)
        action = _minimal_semantic_action(action_payload)
        if action is None:
            if expected_state is not None:
                raise ValueError("complete action cannot include expected_state")
            return BrowserActionProposal(step_index=step_index, step_status="complete")
        return BrowserActionProposal(
            step_index=step_index,
            step_status="in_progress",
            action=action,
            expected_state=expected_state,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ProviderContractError("provider planner response violates action schema") from error


_TARGET_FIELDS = frozenset({"role", "name", "text", "label", "placeholder"})


def _minimal_semantic_action(payload: dict[str, object]) -> dict[str, object] | None:
    action = payload.get("action")
    if action == "complete" and set(payload) == {"action"}:
        return None
    if action == "navigate" and set(payload) == {"action", "url"}:
        return {"type": "navigate", "value": payload["url"]}
    if action == "wait" and set(payload) in ({"action"}, {"action", "value"}):
        result: dict[str, object] = {"type": "wait"}
        if "value" in payload:
            result["value"] = payload["value"]
        return result

    target = {key: payload[key] for key in _TARGET_FIELDS if key in payload}
    if not target:
        raise ValueError("semantic action requires a target")
    target_keys = set(target)
    if action in {"click", "check", "extract_text"} and set(payload) == {"action", *target_keys}:
        return {"type": action, "target": target}
    if action in {"fill", "select"} and set(payload) == {"action", "value", *target_keys}:
        return {"type": action, "target": target, "value": payload["value"]}
    if action == "press" and set(payload) == {"action", "key", *target_keys}:
        return {"type": action, "target": target, "value": payload["key"]}
    raise ValueError("unsupported minimal planner action")


def _safe_error_detail(response: httpx.Response) -> str:
    try:
        detail = response.json().get("error", {}).get("message", "unspecified provider error")
    except (TypeError, ValueError):
        return "unparseable provider error"
    return str(detail).replace("\n", " ")[:300]


def _required_int(usage: dict[str, object], field: str) -> int:
    value = usage.get(field)
    if not isinstance(value, int) or value < 0:
        raise ProviderContractError(f"provider response lacks non-negative {field}")
    return value
