from __future__ import annotations

import pytest

from browser_agent_evaluation.core.budget import BudgetExceeded, ModelBudget


def test_budget_enforces_trial_request_and_cost_limits() -> None:
    budget = ModelBudget(max_total_usd=5.00, max_trial_usd=0.25, max_requests_per_trial=2)
    budget.start_trial("trial-1")
    budget.before_request("trial-1")
    budget.consume("trial-1", 0.10)
    budget.before_request("trial-1")
    budget.consume("trial-1", 0.15)

    with pytest.raises(BudgetExceeded, match="trial cost"):
        budget.before_request("trial-1")


def test_budget_stops_all_trials_at_global_limit() -> None:
    budget = ModelBudget(max_total_usd=0.20, max_trial_usd=0.20, max_requests_per_trial=12)
    budget.start_trial("trial-1")
    budget.before_request("trial-1")
    budget.consume("trial-1", 0.20)
    budget.start_trial("trial-2")

    with pytest.raises(BudgetExceeded, match="global cost"):
        budget.before_request("trial-2")


def test_budget_enforces_cumulative_trial_token_cap() -> None:
    budget = ModelBudget(
        max_total_usd=5.00,
        max_trial_usd=0.25,
        max_requests_per_trial=12,
        max_tokens_per_trial=50_000,
    )
    budget.start_trial("trial-1")
    budget.before_request("trial-1")
    budget.consume_usage("trial-1", 0.01, 40_000, 9_000)
    budget.before_request("trial-1")

    with pytest.raises(BudgetExceeded, match="trial token"):
        budget.consume_usage("trial-1", 0.01, 1_000, 1_000)


def test_budget_rejects_unavailable_cost() -> None:
    budget = ModelBudget(max_total_usd=5.00, max_trial_usd=0.25, max_requests_per_trial=12)
    budget.start_trial("trial-1")

    with pytest.raises(BudgetExceeded, match="provider-reported cost"):
        budget.consume("trial-1", None)
