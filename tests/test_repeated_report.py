from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from browser_agent_evaluation.core.models import TrialEvidence, UsageEvidence
from browser_agent_evaluation.reporting.manifest import (
    EvaluationManifest,
    ManifestLimits,
    ManifestTask,
    write_evaluation_manifest,
)
from browser_agent_evaluation.reporting.repeated import (
    RepeatedReportError,
    load_repeated_evidence,
    render_repeated_report,
)

TASK_IDS = (
    "wikipedia-search-en",
    "mdn-reference-en",
    "selenium-web-form-en",
    "selenium-ajax-labels-en",
    "selenium-key-events-en",
    "marca-real-madrid-open-en",
    "amazon-cheapest-coffee-beans-en",
)
AI_RUNNERS = ("restricted", "browser_use", "playwright_mcp")


def test_selective_refresh_keeps_standard_evidence_and_backups(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from browser_agent_evaluation.cli import refresh, repeat

    original_path = _write_matrix(tmp_path, skip_ai_on_reference_failure=False)
    original_bytes = original_path.read_bytes()
    before = load_repeated_evidence(original_path)
    standard = {
        record.path.name: record.path.read_bytes()
        for record in before.records
        if not record.trial.task_id.startswith(("marca-", "amazon-"))
    }
    monkeypatch.setattr(refresh, "load_local_runtime_environment", lambda _: None)
    monkeypatch.setattr(
        refresh,
        "load_experiment_configuration",
        lambda _: SimpleNamespace(
            provider=SimpleNamespace(endpoint=before.manifest.provider_endpoint)
        ),
    )

    def fake_repeat(argv: list[str]) -> None:
        directory = Path(argv[argv.index("--output-dir") + 1])
        path = _write_matrix(directory, skip_ai_on_reference_failure=False)
        generated = load_repeated_evidence(path)
        filenames = []
        for record in generated.records:
            if record.trial.task_id.startswith(("marca-", "amazon-")):
                name = "replacement-" + record.path.name
                (directory / name).write_bytes(record.path.read_bytes())
                filenames.append(name)
        manifest = generated.manifest.model_copy(
            update={
                "tasks": [
                    task
                    for task in generated.manifest.tasks
                    if task.id.startswith(("marca-", "amazon-"))
                ],
                "artifact_files": filenames,
            }
        )
        write_evaluation_manifest(manifest, output_dir=directory)

    monkeypatch.setattr(repeat, "main", fake_repeat)
    task_root = Path(__file__).parents[1] / "tasks/experimental"
    refresh.main(
        [
            "--manifest",
            str(original_path),
            "--task-path",
            str(task_root / "marca-real-madrid-open-en.yaml"),
            str(task_root / "amazon-cheapest-coffee-beans-en.yaml"),
        ]
    )
    after = load_repeated_evidence(original_path)
    assert len(after.records) == 84
    assert sum(record.path.name.startswith("replacement-") for record in after.records) == 24
    for name, raw in standard.items():
        assert (tmp_path / name).read_bytes() == raw
    assert next(tmp_path.glob("refresh-*/previous-manifest.json")).read_bytes() == original_bytes


def test_report_rejects_forged_open_task_success(tmp_path: Path) -> None:
    manifest_path = _write_matrix(tmp_path, skip_ai_on_reference_failure=False)
    manifest = EvaluationManifest.model_validate_json(manifest_path.read_bytes())
    task = next(task for task in manifest.tasks if task.id.startswith("marca-"))
    task.verification_mode = "task_completion"
    task.verifier = "marca_article"
    for name in manifest.artifact_files:
        path = tmp_path / name
        payload = json.loads(path.read_text())
        if payload["task_id"] == task.id:
            payload["outcome"] = "passed"
            path.write_text(json.dumps(payload))
    write_evaluation_manifest(manifest, output_dir=tmp_path)
    with pytest.raises(RepeatedReportError, match="independent verification"):
        load_repeated_evidence(manifest_path)


def test_open_reference_is_reported_as_control_not_solution(tmp_path: Path) -> None:
    manifest_path = _write_matrix(tmp_path, skip_ai_on_reference_failure=False)
    manifest = EvaluationManifest.model_validate_json(manifest_path.read_bytes())
    task = next(task for task in manifest.tasks if task.id.startswith("marca-"))
    task.verification_mode = "task_completion"
    task.verifier = "marca_article"
    heading = "Real Madrid current article"
    url = "https://www.marca.com/futbol/real-madrid/2026/09/07/current-article.html"
    answer = json.dumps({"name": heading, "url": url})
    for name in manifest.artifact_files:
        path = tmp_path / name
        payload = json.loads(path.read_text())
        if payload["task_id"] == task.id:
            payload["outcome"] = "passed"
            payload["verification_evidence"] = {
                "answer": answer,
                "heading": heading,
                "url": url,
            }
            path.write_text(json.dumps(payload))
    write_evaluation_manifest(manifest, output_dir=tmp_path)

    report = render_repeated_report(load_repeated_evidence(manifest_path))

    assert (
        "| Marca Real Madrid (English) | experimental | Deterministic reference | "
        "N/A (control 3/3) |" in report
    )
    assert "Open-task deterministic references are control checks, not solution claims." in report


def test_manifested_report_keeps_all_seven_tasks_and_reference_skips(tmp_path: Path) -> None:
    manifest_path = _write_matrix(tmp_path)

    report = render_repeated_report(load_repeated_evidence(manifest_path))

    assert "**7 tasks** (5 standard and 2 experimental)" in report
    assert "| Deterministic reference | 14/15 | 6 | 0 | 0 |" in report
    assert "| browser-use | 14/14 | 6 | 0 | 1 |" in report
    assert "0.01900000 + 1 unavailable" in report
    assert "48 model requests and 1,000,000 cumulative tokens" in report
    assert "| Marca Real Madrid (English) | experimental |" in report
    assert "| Amazon cheapest coffee beans (English) | experimental |" in report


def test_manifested_report_rejects_missing_attempt_after_reference_pass(tmp_path: Path) -> None:
    manifest_path = _write_matrix(tmp_path)
    manifest = EvaluationManifest.model_validate_json(manifest_path.read_bytes())
    omitted = next(
        name for name in manifest.artifact_files if name.startswith("restricted-mdn-reference-en")
    )
    manifest_path.write_text(
        manifest.model_copy(
            update={"artifact_files": [name for name in manifest.artifact_files if name != omitted]}
        ).model_dump_json(),
        encoding="utf-8",
    )

    with pytest.raises(RepeatedReportError, match="requires 3 trials under the manifested"):
        load_repeated_evidence(manifest_path)


def test_default_reference_policy_keeps_every_task_in_ai_matrix(tmp_path: Path) -> None:
    manifest_path = _write_matrix(
        tmp_path,
        skip_ai_on_reference_failure=False,
        all_browser_use_costs_unknown=True,
    )

    report = render_repeated_report(load_repeated_evidence(manifest_path))

    assert "| Reference policy | always run AI |" in report
    assert "| browser-use | 15/15 | 6 | 0 | 0 |" in report
    assert "unavailable (21 trials)" in report
    assert "## Aggregate observations" in report
    assert "Highest observed AI success rate: Restricted agent (15/15)" in report
    assert "A complete cost ranking is unavailable" in report


def test_report_discloses_execution_notes(tmp_path: Path) -> None:
    manifest_path = _write_matrix(tmp_path)
    manifest = EvaluationManifest.model_validate_json(manifest_path.read_bytes())
    write_evaluation_manifest(
        manifest.model_copy(update={"execution_notes": ["Reference-only repair."]}),
        output_dir=tmp_path,
    )

    report = render_repeated_report(load_repeated_evidence(manifest_path))

    assert "### Execution notes" in report
    assert "- Reference-only repair." in report


def _write_matrix(
    tmp_path: Path,
    *,
    skip_ai_on_reference_failure: bool = True,
    all_browser_use_costs_unknown: bool = False,
) -> Path:
    started = datetime(2026, 9, 7, tzinfo=UTC)
    filenames: list[str] = []
    for task_id in TASK_IDS:
        reference_passes = 2 if task_id == "wikipedia-search-en" else 3
        for repetition in range(3):
            reference_passed = repetition < reference_passes
            filenames.append(
                _write_trial(
                    tmp_path,
                    task_id=task_id,
                    runner="playwright_reference",
                    repetition=repetition,
                    passed=reference_passed,
                    started=started,
                )
            )
        for runner in AI_RUNNERS:
            ai_repetitions = reference_passes if skip_ai_on_reference_failure else 3
            for repetition in range(ai_repetitions):
                filenames.append(
                    _write_trial(
                        tmp_path,
                        task_id=task_id,
                        runner=runner,
                        repetition=repetition,
                        passed=True,
                        started=started,
                        unknown_cost=(
                            runner == "browser_use"
                            and (
                                all_browser_use_costs_unknown
                                or (task_id == "mdn-reference-en" and repetition == 0)
                            )
                        ),
                    )
                )

    manifest = EvaluationManifest(
        created_at=started,
        task_language="en",
        tasks=[
            ManifestTask(
                id=task_id,
                category=(
                    "experimental" if task_id.startswith(("marca-", "amazon-")) else "standard"
                ),
                source=f"{task_id}.yaml",
                contract_sha256="a" * 64,
                max_actions=48,
                timeout_seconds=300,
                acceptance_fields=["visible_text"],
                verification_mode=(
                    "reachability"
                    if task_id.startswith(("marca-", "amazon-"))
                    else "task_completion"
                ),
            )
            for task_id in TASK_IDS
        ],
        ai_runners=list(AI_RUNNERS),
        repetitions=3,
        round_indices=[1, 2, 3],
        round_seeds=[7, 8, 9],
        model="gpt-5.6-luna",
        provider_endpoint="https://api.openai.com/v1",
        reference_browser_version="Chromium 151.0",
        browser_use_browser_version="Chromium 140.0",
        rendering_profile="visual-parity",
        headless=True,
        skip_ai_on_reference_failure=skip_ai_on_reference_failure,
        limits=ManifestLimits(
            max_total_usd_per_round=2.0,
            max_trial_usd=0.25,
            max_requests_per_trial=48,
            max_tokens_per_trial=1_000_000,
        ),
        artifact_files=filenames,
    )
    return write_evaluation_manifest(manifest, output_dir=tmp_path)


def _write_trial(
    directory: Path,
    *,
    task_id: str,
    runner: str,
    repetition: int,
    passed: bool,
    started: datetime,
    unknown_cost: bool = False,
) -> str:
    is_reference = runner == "playwright_reference"
    trial = TrialEvidence(
        trial_id=f"{runner}-{task_id}-r{repetition}",
        task_id=task_id,
        runner=runner,  # type: ignore[arg-type]
        model_id=None if is_reference else "gpt-5.6-luna",
        started_at=started,
        ended_at=started + timedelta(seconds=repetition + 1),
        duration_ms=(repetition + 1) * 1_000,
        outcome=(
            "unverified"
            if passed and task_id.startswith(("marca-", "amazon-"))
            else "passed"
            if passed
            else "failed"
        ),
        action_count=0 if is_reference else 2,
        retry_count=0,
        cleanup_verified=True,
        assertion_results={"visible_text": passed},
        policy_events=[] if passed else ["reference_failed"],
        observation_mode="reference" if is_reference else "framework_owned",
        usage=UsageEvidence(
            prompt_tokens=None if is_reference else 100,
            completion_tokens=None if is_reference else 10,
            request_count=0 if is_reference else 1,
            cost_usd=None if is_reference or unknown_cost else 0.001,
            unavailable_reason=(
                "reference run uses no model"
                if is_reference
                else "provider cost unavailable"
                if unknown_cost
                else None
            ),
        ),
    )
    filename = f"{trial.trial_id}.json"
    payload = trial.model_dump(mode="json")
    payload.update({"trace": "sanitized", "trace_sha256": "sha256:test"})
    (directory / filename).write_text(json.dumps(payload), encoding="utf-8")
    return filename
