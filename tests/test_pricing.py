from browser_agent_evaluation.pricing import provider_cost_or_luna_estimate


def test_estimates_luna_standard_cost_including_cached_input() -> None:
    estimate = provider_cost_or_luna_estimate(
        {
            "prompt_tokens": 1_000_000,
            "completion_tokens": 1_000_000,
            "prompt_tokens_details": {"cached_tokens": 250_000},
        }
    )

    assert estimate == 2.11


def test_prefers_provider_reported_cost() -> None:
    assert provider_cost_or_luna_estimate(
        {"prompt_tokens": 1, "completion_tokens": 1, "cost": 0.123}
    ) == 0.123
