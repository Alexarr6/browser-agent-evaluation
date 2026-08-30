from browser_agent_evaluation.core.pricing import provider_cost_or_model_estimate


def test_estimates_known_model_cost_including_cached_input() -> None:
    estimate = provider_cost_or_model_estimate(
        {
            "prompt_tokens": 1_000_000,
            "completion_tokens": 1_000_000,
            "prompt_tokens_details": {"cached_tokens": 250_000},
        },
        model="gpt-5.6-luna",
    )

    assert estimate == 2.11


def test_prefers_provider_reported_cost_for_any_model() -> None:
    assert (
        provider_cost_or_model_estimate(
            {"prompt_tokens": 1, "completion_tokens": 1, "cost": 0.123},
            model="other-model",
        )
        == 0.123
    )


def test_does_not_apply_one_models_pricing_to_an_unknown_model() -> None:
    assert (
        provider_cost_or_model_estimate(
            {"prompt_tokens": 1, "completion_tokens": 1}, model="other-model"
        )
        is None
    )
