from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from browser_agent_evaluation.core.models import TrialEvidence, UsageEvidence
from browser_agent_evaluation.reporting.comparison import (
    load_comparable_evidence,
    render_comparison_report,
)


def test_report_requires_complete_valid_matrix_and_renders_aggregates(tmp_path: Path) -> None:
    paths = _matrix(tmp_path)
    wrapped = json.loads(paths[0].read_text(encoding="utf-8"))
    wrapped.update({"trace": "accepted", "trace_sha256": "sha256:test"})
    paths[0].write_text(json.dumps(wrapped), encoding="utf-8")

    evidence = load_comparable_evidence(paths)
    report = render_comparison_report(
        evidence,
        known_total_spend_usd=0.04,
        unknown_cost_reservations=2,
        reservation_usd=0.25,
    )

    assert len(evidence) == 8
    assert "| Restricted agent | 2/2 | 1.500 | 4 | 200 | 40 | 240 | 0.00200000 |" in report
    assert "conservative total of USD 0.54000000" in report
    assert report.count("SHA-256") == 1


def test_report_includes_failed_trial_in_success_rate_and_spend(tmp_path: Path) -> None:
    paths = _matrix(tmp_path)
    failed = TrialEvidence.model_validate_json(paths[1].read_bytes()).model_copy(
        update={"outcome": "failed", "assertion_results": {"final": False}}
    )
    paths[1].write_text(failed.model_dump_json(), encoding="utf-8")

    report = render_comparison_report(
        load_comparable_evidence(paths),
        known_total_spend_usd=0.04,
        unknown_cost_reservations=0,
        reservation_usd=0.25,
    )

    assert "| Restricted agent | 1/2 | 2.000 | 4 | 200 | 40 | 240 | 0.00200000 |" in report
    assert "| Wikipedia | Restricted agent | failed |" in report


def test_report_rejects_trial_without_cleanup(tmp_path: Path) -> None:
    paths = _matrix(tmp_path)
    invalid = TrialEvidence.model_validate_json(paths[0].read_bytes()).model_copy(
        update={"cleanup_verified": False}
    )
    paths[0].write_text(invalid.model_dump_json(), encoding="utf-8")

    with pytest.raises(ValueError, match="lacks cleanup evidence"):
        load_comparable_evidence(paths)


def _matrix(tmp_path: Path) -> list[Path]:
    paths: list[Path] = []
    started = datetime(2026, 8, 24, tzinfo=UTC)
    for task_index, task in enumerate(("wikipedia-search", "mdn-reference")):
        for runner_index, runner in enumerate(
            ("playwright_reference", "restricted", "browser_use", "playwright_mcp")
        ):
            is_reference = runner == "playwright_reference"
            evidence = TrialEvidence(
                trial_id=f"{runner}-{task}",
                task_id=task,
                runner=runner,  # type: ignore[arg-type]
                started_at=started,
                ended_at=started + timedelta(seconds=task_index + 1),
                duration_ms=(task_index + 1) * 1_000,
                outcome="passed",
                action_count=runner_index + 1,
                retry_count=0,
                cleanup_verified=True,
                assertion_results={"final": True},
                policy_events=[],
                observation_mode=("reference" if is_reference else "framework_owned"),
                usage=UsageEvidence(
                    prompt_tokens=None if is_reference else 100,
                    completion_tokens=None if is_reference else 20,
                    request_count=0 if is_reference else 2,
                    cost_usd=None if is_reference else 0.001,
                    unavailable_reason="reference run uses no model" if is_reference else None,
                ),
            )
            path = tmp_path / f"{runner}-{task}.json"
            path.write_text(evidence.model_dump_json(), encoding="utf-8")
            paths.append(path)
    return paths
