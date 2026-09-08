"""Independent checks of browser-owned facts and the runner's final answer."""

from __future__ import annotations

import json
import re
from decimal import Decimal
from urllib.parse import urlsplit


def normalized(value: str) -> str:
    return " ".join(value.split())


def resource_identity(value: object, verifier: str) -> str | None:
    """Identify a resource independently of tracking and URL presentation."""
    if not isinstance(value, str):
        return None
    try:
        parsed = urlsplit(value)
        if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port:
            return None
    except ValueError:
        return None
    if verifier == "marca_article":
        if parsed.hostname in {"marca.com", "www.marca.com"} and re.fullmatch(
            r"/futbol/real-madrid/\d{4}/\d{2}/\d{2}/[^/]+\.html", parsed.path
        ):
            return parsed.path
    elif parsed.hostname in {"amazon.es", "www.amazon.es"}:
        match = re.fullmatch(r"/(?:[^/]+/)?(?:dp|gp/product)/([A-Z0-9]{10})(?:/.*)?", parsed.path)
        if match:
            return match.group(1)
    return None


def unit_price(text: str) -> Decimal | None:
    values = {
        Decimal(match.replace(".", "").replace(",", ".") if "," in match else match)
        for match in re.findall(
            r"(?<![\d.,])(\d+(?:[.,]\d{1,2})?)\s*(?:€|EUR)\s*/\s*(?:kg|kilogramo)\b", text, re.I
        )
    }
    return next(iter(values)) if len(values) == 1 else None


def verify_open(verifier: str, facts: dict[str, str], answer: str) -> dict[str, bool]:
    try:
        claim = json.loads(answer)
    except (ValueError, TypeError):
        claim = {}
    if not isinstance(claim, dict):
        claim = {}
    url = facts.get("url", "")
    parsed = urlsplit(url)
    heading = normalized(facts.get("heading", ""))
    checks = {
        "observed_heading": bool(heading),
        "answer_name_matches": isinstance(claim.get("name"), str)
        and bool(heading)
        and normalized(claim["name"]) == heading,
        "answer_url_matches": resource_identity(url, verifier) is not None
        and resource_identity(claim.get("url"), verifier) == resource_identity(url, verifier),
    }
    if verifier == "marca_article":
        checks["article_url"] = (
            parsed.scheme == "https"
            and parsed.hostname in {"marca.com", "www.marca.com"}
            and bool(
                re.fullmatch(r"/futbol/real-madrid/\d{4}/\d{2}/\d{2}/[^/]+\.html", parsed.path)
            )
        )
    else:
        checks["product_url"] = (
            parsed.scheme == "https"
            and parsed.hostname in {"amazon.es", "www.amazon.es"}
            and bool(re.search(r"/(?:dp|gp/product)/[A-Z0-9]{10}(?:/|$)", parsed.path))
        )
        checks["coffee_beans"] = bool(re.search(r"caf[eé].*grano|coffee.*beans", heading, re.I))
        checks["not_accessory_or_ground"] = not bool(
            re.search(
                r"\b(molido|ground|capsul\w*|cápsul\w*|cafetera\w*|máquina\w*|machine\w*|pods)\b",
                heading,
                re.I,
            )
        )
        price = unit_price(facts.get("price_text", ""))
        checks["unit_price_observed"] = price is not None
        checks["below_14_eur_kg"] = price is not None and Decimal(0) < price < Decimal(14)
        try:
            checks["answer_price_matches"] = (
                price is not None and Decimal(str(claim.get("eur_per_kg"))) == price
            )
        except Exception:
            checks["answer_price_matches"] = False
    return checks
