from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from browser_agent_evaluation.core.models import TrialEvidence, UsageEvidence
from browser_agent_evaluation.reporting.evidence import redact_and_bound, write_trial_evidence


def evidence() -> TrialEvidence:
    timestamp = datetime(2026, 8, 24, tzinfo=UTC)
    return TrialEvidence(
        trial_id="trial-001",
        task_id="wikipedia-search",
        runner="restricted",
        started_at=timestamp,
        ended_at=timestamp,
        outcome="passed",
        duration_ms=12,
        action_count=2,
        retry_count=0,
        cleanup_verified=True,
        assertion_results={"title": True},
        observation_mode="accessibility_dom",
        usage=UsageEvidence(request_count=0, unavailable_reason="no model request"),
    )


def test_redaction_happens_before_utf8_safe_truncation() -> None:
    result = redact_and_bound(
        "secret-token ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        markers=["secret-token"],
        max_bytes=20,
    )

    assert result.text.startswith("[REDACTED]")
    assert "secret-token" not in result.text
    assert "marker" in result.events


def test_trial_summary_is_redacted_and_atomic(tmp_path: Path) -> None:
    path = write_trial_evidence(
        evidence(),
        output_dir=tmp_path,
        raw_trace="Authorization: secret-token\n/home/pi/private\n",
        markers=["secret-token"],
        forbidden_paths=["/home/pi/private"],
        max_trace_bytes=200,
    )

    payload = json.loads(path.read_text("utf-8"))
    assert payload["trial_id"] == "trial-001"
    assert "secret-token" not in payload["trace"]
    assert "/home/pi/private" not in payload["trace"]
    assert payload["trace_redaction_events"] == ["marker", "path"]


@pytest.mark.parametrize("outcome", ["passed", "unverified"])
def test_positive_outcomes_require_positive_assertions(outcome: str) -> None:
    payload = evidence().model_dump()
    payload.update({"outcome": outcome, "assertion_results": {}})

    with pytest.raises(ValidationError, match="successful independent assertions"):
        TrialEvidence.model_validate(payload)
