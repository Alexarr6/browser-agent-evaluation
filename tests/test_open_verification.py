import json

import pytest

from browser_agent_evaluation.browser.keys import normalize_key
from browser_agent_evaluation.core.models import BrowserActionProposal
from browser_agent_evaluation.core.open_verification import verify_open


def test_marca_checks_heading_and_final_article_not_homepage() -> None:
    facts = {
        "heading": "Cestero y Sergio levantan la mano",
        "url": "https://www.marca.com/futbol/real-madrid/2026/09/07/article.html",
    }
    answer = json.dumps({"name": facts["heading"], "url": facts["url"]})
    assert all(verify_open("marca_article", facts, answer).values())
    assert not all(
        verify_open("marca_article", {**facts, "url": "https://www.marca.com/"}, answer).values()
    )
    assert not all(verify_open("marca_article", facts, '{"name":"invented"}').values())


@pytest.mark.parametrize("price,expected", [("13,99", True), ("14,00", False), ("14,01", False)])
def test_amazon_threshold_is_strict_and_name_matches(price: str, expected: bool) -> None:
    facts = {
        "heading": "Cafe en grano 1 kg",
        "url": "https://www.amazon.es/dp/B012345678",
        "price_text": price + " € / kg",
    }
    answer = json.dumps(
        {
            "name": facts["heading"],
            "url": facts["url"],
            "eur_per_kg": float(price.replace(",", ".")),
        }
    )
    assert all(verify_open("amazon_coffee_under_14", facts, answer).values()) is expected
    assert not all(
        verify_open("amazon_coffee_under_14", {**facts, "price_text": ""}, answer).values()
    )
    assert not all(
        verify_open("amazon_coffee_under_14", {**facts, "heading": "Cafe molido"}, answer).values()
    )


def test_conflicting_prices_do_not_pass() -> None:
    facts = {
        "heading": "Cafe en grano",
        "url": "https://www.amazon.es/dp/B012345678",
        "price_text": "12,00 €/kg 18,00 €/kg",
    }
    answer = json.dumps({"name": facts["heading"], "url": facts["url"], "eur_per_kg": 12})
    assert not all(verify_open("amazon_coffee_under_14", facts, answer).values())


@pytest.mark.parametrize(
    "claimed_url,expected",
    [
        ("https://amazon.es/dp/B012345678", True),
        ("https://www.amazon.es/gp/product/B012345678?th=1", True),
        ("https://www.amazon.es/dp/B012345679", False),
        ("https://evil.test/dp/B012345678", False),
        ("https://www.amazon.es/", False),
        ("https://www.amazon.es@evil.test/dp/B012345678", False),
    ],
)
def test_product_identity_ignores_tracking_but_requires_same_asin(
    claimed_url: str, expected: bool
) -> None:
    facts = {
        "heading": "Cafe en grano",
        "url": "https://www.amazon.es/coffee/dp/B012345678/ref=sr_1?keywords=cafe%2Bgrano&th=1",
        "price_text": "10,56 €/kg",
    }
    answer = json.dumps({"name": facts["heading"], "url": claimed_url, "eur_per_kg": 10.56})
    assert all(verify_open("amazon_coffee_under_14", facts, answer).values()) is expected


def test_article_tracking_is_irrelevant_but_different_article_fails() -> None:
    url = "https://www.marca.com/futbol/real-madrid/2026/09/07/article.html"
    facts = {"heading": "Headline", "url": url + "?utm_source=home#top"}
    for claim, expected in [(url, True), (url.replace("article.html", "other.html"), False)]:
        answer = json.dumps({"name": "Headline", "url": claim})
        assert all(verify_open("marca_article", facts, answer).values()) is expected


def test_structured_restricted_result_is_serialized_without_inventing_evidence() -> None:
    claim = {"name": "Title", "url": "https://www.marca.com/"}
    proposal = BrowserActionProposal.model_validate(
        {"step_index": 1, "step_status": "complete", "result": claim}
    )
    assert json.loads(proposal.result) == claim


def test_key_spelling_normalization_preserves_character_case_and_unknown_keys() -> None:
    assert normalize_key("ENTER") == "Enter"
    assert normalize_key("HOME") == "Home"
    assert normalize_key("a") == "a"
    assert normalize_key("A") == "A"
    assert normalize_key("unknown") == "unknown"
