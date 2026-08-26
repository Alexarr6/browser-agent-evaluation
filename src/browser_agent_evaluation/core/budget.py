from __future__ import annotations

from dataclasses import dataclass, field


class BudgetExceeded(RuntimeError):
    """Raised before a model request can exceed the approved evaluation budget."""


@dataclass
class ModelBudget:
    max_total_usd: float | None
    max_trial_usd: float | None
    max_requests_per_trial: int
    max_tokens_per_trial: int | None = None
    total_spend_usd: float = 0.0
    _trial_spend: dict[str, float] = field(default_factory=dict)
    _trial_requests: dict[str, int] = field(default_factory=dict)
    _trial_tokens: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.max_requests_per_trial <= 0:
            raise ValueError("request cap must be positive")
        if (self.max_total_usd is None) != (self.max_trial_usd is None):
            raise ValueError("cost caps must be configured together or both omitted")
        if self.max_total_usd is not None and self.max_trial_usd is not None:
            if self.max_total_usd <= 0 or self.max_trial_usd <= 0:
                raise ValueError("cost caps must be positive")
            if self.max_trial_usd > self.max_total_usd:
                raise ValueError("trial cost cap cannot exceed global cost cap")
        if self.max_tokens_per_trial is not None and self.max_tokens_per_trial <= 0:
            raise ValueError("trial token cap must be positive when configured")

    def start_trial(self, trial_id: str) -> None:
        if not trial_id or trial_id in self._trial_spend:
            raise ValueError("trial id must be new and non-empty")
        self._trial_spend[trial_id] = 0.0
        self._trial_requests[trial_id] = 0
        self._trial_tokens[trial_id] = 0

    def before_request(self, trial_id: str) -> None:
        if trial_id not in self._trial_spend:
            raise ValueError("trial has not started")
        if self.max_total_usd is not None and self.total_spend_usd >= self.max_total_usd:
            raise BudgetExceeded("global cost cap reached")
        if self.max_trial_usd is not None and self._trial_spend[trial_id] >= self.max_trial_usd:
            raise BudgetExceeded("trial cost cap reached")
        if self._trial_requests[trial_id] >= self.max_requests_per_trial:
            raise BudgetExceeded("trial request cap reached")
        if (
            self.max_tokens_per_trial is not None
            and self._trial_tokens[trial_id] >= self.max_tokens_per_trial
        ):
            raise BudgetExceeded("trial token cap reached")
        self._trial_requests[trial_id] += 1

    def consume_usage(
        self,
        trial_id: str,
        cost_usd: float | None,
        prompt_tokens: int | None,
        completion_tokens: int | None,
    ) -> None:
        if prompt_tokens is None or completion_tokens is None:
            raise BudgetExceeded("provider-reported token usage is required")
        if prompt_tokens < 0 or completion_tokens < 0:
            raise ValueError("token usage must not be negative")
        if trial_id not in self._trial_tokens:
            raise ValueError("trial has not started")
        token_count = prompt_tokens + completion_tokens
        if (
            self.max_tokens_per_trial is not None
            and self._trial_tokens[trial_id] + token_count > self.max_tokens_per_trial
        ):
            raise BudgetExceeded("trial token cap exceeded")
        self.consume(trial_id, cost_usd)
        self._trial_tokens[trial_id] += token_count

    def consume(self, trial_id: str, cost_usd: float | None) -> None:
        if cost_usd is None:
            if self.max_total_usd is not None:
                raise BudgetExceeded("provider-reported cost is required")
            return
        if cost_usd < 0:
            raise ValueError("cost must not be negative")
        if trial_id not in self._trial_spend:
            raise ValueError("trial has not started")
        if (
            self.max_trial_usd is not None
            and self._trial_spend[trial_id] + cost_usd > self.max_trial_usd
        ):
            raise BudgetExceeded("trial cost cap exceeded")
        if (
            self.max_total_usd is not None
            and self.total_spend_usd + cost_usd > self.max_total_usd
        ):
            raise BudgetExceeded("global cost cap exceeded")
        self._trial_spend[trial_id] += cost_usd
        self.total_spend_usd += cost_usd
