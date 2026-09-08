from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import median

from browser_agent_evaluation.core.models import RunnerName, TrialEvidence
from browser_agent_evaluation.core.open_verification import verify_open
from browser_agent_evaluation.reporting.comparison import RUNNER_LABELS, TASK_LABELS
from browser_agent_evaluation.reporting.manifest import (
    EvaluationManifest,
    ManifestTask,
    load_evaluation_manifest,
)


class RepeatedReportError(ValueError):
    """Raised when a manifested repeated evidence set is incomplete or invalid."""


@dataclass(frozen=True)
class EvidenceRecord:
    path: Path
    sha256: str
    trial: TrialEvidence


@dataclass(frozen=True)
class RepeatedEvidence:
    manifest_path: Path
    manifest: EvaluationManifest
    records: tuple[EvidenceRecord, ...]


def load_repeated_evidence(manifest_path: Path) -> RepeatedEvidence:
    manifest = load_evaluation_manifest(manifest_path)
    records: list[EvidenceRecord] = []
    trial_ids: set[str] = set()
    task_ids = {task.id for task in manifest.tasks}
    task_by_id = {task.id: task for task in manifest.tasks}
    runner_ids = {"playwright_reference", *manifest.ai_runners}

    for filename in manifest.artifact_files:
        path = manifest_path.parent / filename
        if not path.is_file():
            raise RepeatedReportError(f"manifested evidence does not exist: {path}")
        raw = path.read_bytes()
        envelope = json.loads(raw)
        if not isinstance(envelope, dict):
            raise RepeatedReportError(f"evidence is not a JSON object: {path}")
        trial = TrialEvidence.model_validate(
            {key: value for key, value in envelope.items() if key in TrialEvidence.model_fields}
        )
        if trial.trial_id in trial_ids:
            raise RepeatedReportError(f"duplicate trial id: {trial.trial_id}")
        if trial.task_id not in task_ids:
            raise RepeatedReportError(f"evidence task is outside the manifest: {path}")
        if trial.runner not in runner_ids:
            raise RepeatedReportError(f"evidence runner is outside the manifest: {path}")
        if not trial.cleanup_verified and trial.outcome != "invalidated":
            raise RepeatedReportError(f"non-invalidated trial lacks verified cleanup: {path}")
        if trial.outcome == "passed" and (
            not trial.assertion_results or not all(trial.assertion_results.values())
        ):
            raise RepeatedReportError(f"passing trial lacks successful assertions: {path}")
        verification_mode = task_by_id[trial.task_id].verification_mode
        verifier = task_by_id[trial.task_id].verifier
        if verifier and trial.outcome == "passed":
            facts = trial.verification_evidence
            if not all(verify_open(verifier, facts, facts.get("answer", "")).values()):
                raise RepeatedReportError(f"passing trial fails independent verification: {path}")
        if verification_mode == "reachability" and trial.outcome == "passed":
            raise RepeatedReportError(
                f"reachability-only trial cannot claim task completion: {path}"
            )
        if verification_mode == "task_completion" and trial.outcome == "unverified":
            raise RepeatedReportError(
                f"task-completion trial cannot be marked unverified: {path}"
            )
        trial_ids.add(trial.trial_id)
        records.append(
            EvidenceRecord(path=path, sha256=hashlib.sha256(raw).hexdigest(), trial=trial)
        )

    grouped = _group_records(records)
    for task in manifest.tasks:
        references = grouped[(task.id, "playwright_reference")]
        if len(references) != manifest.repetitions:
            raise RepeatedReportError(
                f"{task.id} requires {manifest.repetitions} reference trials; "
                f"found {len(references)}"
            )
        reference_passes = sum(
            record.trial.outcome in {"passed", "unverified"} for record in references
        )
        expected_ai_trials = (
            reference_passes
            if manifest.skip_ai_on_reference_failure and task.verifier is None
            else manifest.repetitions
        )
        for runner in manifest.ai_runners:
            attempts = grouped[(task.id, runner)]
            if len(attempts) != expected_ai_trials:
                raise RepeatedReportError(
                    f"{task.id}/{runner} requires {expected_ai_trials} trials under the "
                    f"manifested reference policy; found {len(attempts)}"
                )

    return RepeatedEvidence(
        manifest_path=manifest_path,
        manifest=manifest,
        records=tuple(records),
    )


def render_repeated_report(evidence: RepeatedEvidence) -> str:
    manifest = evidence.manifest
    grouped = _group_records(evidence.records)
    runners: list[RunnerName] = ["playwright_reference", *manifest.ai_runners]
    standard_count = sum(task.category == "standard" for task in manifest.tasks)
    experimental_count = len(manifest.tasks) - standard_count
    planned_slots = len(manifest.tasks) * manifest.repetitions * len(runners)
    lines = [
        "# Repeated browser-agent evaluation",
        "",
        f"This report covers one unified matrix of **{len(manifest.tasks)} tasks** "
        f"({standard_count} standard and {experimental_count} experimental), "
        f"{manifest.repetitions} repetitions and {len(runners)} runners. Every task is mandatory "
        "in the execution matrix. Tasks with reachability-only checks are reported as "
        "unverified and never counted as completed.",
        "",
        "> `passed` is reserved for task-completion contracts. A successful "
        "reachability-only check is `unverified`, never a completed task.",
        "",
        "> Open-task deterministic references are control checks, not solution claims. "
        "They validate current site and verifier feasibility but are excluded from "
        "solution denominators.",
        "",
        "## Run configuration",
        "",
        "| Property | Value |",
        "|---|---|",
        f"| Created | {manifest.created_at.isoformat()} |",
        f"| Language | {manifest.task_language} |",
        f"| Model | `{manifest.model}` |",
        f"| Provider endpoint | `{manifest.provider_endpoint}` |",
        f"| Rendering | `{manifest.rendering_profile}` |",
        f"| Browser mode | {'headless' if manifest.headless else 'headed'} |",
        "| Reference policy | "
        f"{'skip AI on failure' if manifest.skip_ai_on_reference_failure else 'always run AI'} |",
        f"| Rounds | {', '.join(map(str, manifest.round_indices))} |",
        f"| Seeds | {', '.join(map(str, manifest.round_seeds))} |",
        f"| Planned trial slots | {planned_slots} |",
        "| Reference/MCP/restricted browser | "
        f"{_text_or_unavailable(manifest.reference_browser_version)} |",
        f"| browser-use browser | {_text_or_unavailable(manifest.browser_use_browser_version)} |",
    ]
    if manifest.execution_notes:
        lines.extend(
            [
                "",
                "### Execution notes",
                "",
                *(f"- {note}" for note in manifest.execution_notes),
            ]
        )
    lines.extend(
        [
            "",
            "## Task contracts",
            "",
            "| Task | Category | Verification | Assertions | Timeout | Action cap | Contract |",
            "|---|---|---|---|---:|---:|---|",
        ]
    )
    for task in manifest.tasks:
        lines.append(
            f"| {_task_label(task)} | {task.category} | `{task.verification_mode}` | "
            f"{', '.join(f'`{field}`' for field in task.acceptance_fields)} | "
            f"{task.timeout_seconds}s | {task.max_actions} | "
            f"`{task.source}` (`{task.contract_sha256[:12]}`) |"
        )

    lines.extend(
        [
            "",
            "## Per-task results",
            "",
            "`Verified success` is available only for task-completion contracts. Open-task "
            "deterministic references are shown as `N/A (control x/y)` because their "
            "site-specific recipes are controls, not general solutions. `Unverified` means "
            "that a reachability probe succeeded without proving the task instruction. "
            "`Invalid` identifies trials without comparable cleanup evidence. `Ref-skipped` "
            "records planned AI trials that were not started because the deterministic "
            "reference failed.",
            "",
            "| Task | Category | Runner | Verified success | Unverified | Invalid | Ref-skipped | "
            "Median accepted time | Requests | Tokens | Cost (USD) |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    by_runner: dict[RunnerName, list[EvidenceRecord]] = defaultdict(list)
    skipped_by_runner: dict[RunnerName, int] = defaultdict(int)
    for task in manifest.tasks:
        for runner in runners:
            records = grouped[(task.id, runner)]
            by_runner[runner].extend(records)
            skipped = 0 if runner == "playwright_reference" else manifest.repetitions - len(records)
            skipped_by_runner[runner] += skipped
            lines.append(_result_row(task, runner, records, skipped))

    lines.extend(
        [
            "",
            "## Runner aggregate",
            "",
            "Verified-success denominators contain only task-completion contracts. The "
            "deterministic reference denominator excludes verifier-backed open tasks because "
            "those recipes are controls rather than general solutions. Consumption totals "
            "contain every attempted task, including reachability-only tasks and failures.",
            "",
            "| Runner | Verified success | Unverified | Invalid | Ref-skipped | "
            "Median verified time | Requests | Tokens | Cost (USD) |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for runner in runners:
        verified_records = [
            record
            for task in manifest.tasks
            if task.verification_mode == "task_completion"
            and not _is_open_reference_control(task, runner)
            for record in grouped[(task.id, runner)]
        ]
        lines.append(
            _aggregate_row(
                runner,
                by_runner[runner],
                verified_records,
                skipped_by_runner[runner],
            )
        )

    lines.extend(
        [
            "",
            "## Aggregate observations",
            "",
            *_aggregate_observations(manifest, grouped, by_runner),
        ]
    )

    limits = manifest.limits
    total_cost_limit = (
        "not configured"
        if limits.max_total_usd_per_round is None
        else f"USD {limits.max_total_usd_per_round:.2f} per round"
    )
    trial_cost_limit = (
        "not configured"
        if limits.max_trial_usd is None
        else f"USD {limits.max_trial_usd:.2f}"
    )
    token_limit = (
        "not configured"
        if limits.max_tokens_per_trial is None
        else f"{limits.max_tokens_per_trial:,}"
    )
    lines.extend(
        [
            "",
            "## Limits and interpretation warnings",
            "",
            f"- Cost limit: {total_cost_limit}; per-trial limit: {trial_cost_limit}.",
            f"- Per-trial limits: {limits.max_requests_per_trial} model requests and "
            f"{token_limit} cumulative tokens. Task-specific time and action limits appear "
            "above.",
            "- Failed and invalidated attempts remain in request, token and known-cost totals. "
            "Missing tokens or cost are labelled unavailable rather than converted to zero.",
            "- Verifier-backed open-task references are site and verifier controls. Their "
            "site-specific recipes are excluded from solution claims and method rankings.",
            "- Reference failures are site-health signals. AI trials still run unless the "
            "manifest explicitly enables reference-failure skipping; any skipped cells are not "
            "AI successes or failures.",
            "- Reachability-only tasks are mandatory members of this run, but successful probes "
            "are unverified and excluded from task-completion success rates.",
            "- Action counts are omitted from the comparison because framework-native actions are "
            "not equivalent across runners.",
            "- Public websites, provider limits and framework startup can affect outcomes and "
            "end-to-end duration. Repetitions reduce, but do not remove, those confounds.",
            "",
            "## Evidence manifest",
            "",
            f"Run manifest: `{evidence.manifest_path.name}`",
            "",
            "| Trial | Task | Runner | Outcome | Evidence | SHA-256 |",
            "|---|---|---|---|---|---|",
        ]
    )
    for record in sorted(evidence.records, key=lambda item: item.trial.trial_id):
        trial = record.trial
        lines.append(
            f"| `{trial.trial_id}` | `{trial.task_id}` | {RUNNER_LABELS[trial.runner]} | "
            f"{trial.outcome} | `{record.path.name}` | `{record.sha256}` |"
        )
    lines.append("")
    return "\n".join(lines)


def write_repeated_report(*, manifest_path: Path, output_path: Path) -> Path:
    report = render_repeated_report(load_repeated_evidence(manifest_path))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    return output_path


def _group_records(
    records: list[EvidenceRecord] | tuple[EvidenceRecord, ...],
) -> dict[tuple[str, RunnerName], list[EvidenceRecord]]:
    grouped: dict[tuple[str, RunnerName], list[EvidenceRecord]] = defaultdict(list)
    for record in records:
        grouped[(record.trial.task_id, record.trial.runner)].append(record)
    return grouped


def _task_label(task: ManifestTask) -> str:
    if task.verifier == "amazon_coffee_under_14":
        return "Amazon coffee beans below 14 EUR/kg (English)"
    return TASK_LABELS.get(task.id, task.id)


def _result_row(
    task: ManifestTask,
    runner: RunnerName,
    records: list[EvidenceRecord],
    skipped: int,
) -> str:
    trials = [record.trial for record in records]
    valid = [trial for trial in trials if trial.outcome != "invalidated"]
    passing = [trial for trial in valid if trial.outcome == "passed"]
    unverified = [trial for trial in valid if trial.outcome == "unverified"]
    invalid = sum(trial.outcome == "invalidated" for trial in trials)
    if _is_open_reference_control(task, runner):
        success = f"N/A (control {len(passing)}/{len(valid)})"
    elif task.verification_mode == "task_completion":
        success = f"{len(passing)}/{len(valid)}"
    else:
        success = "N/A"
    return (
        f"| {_task_label(task)} | {task.category} | {RUNNER_LABELS[runner]} | "
        f"{success} | {len(unverified)} | {invalid} | {skipped} | "
        f"{_median_passing_time([*passing, *unverified])} | "
        f"{sum(trial.usage.request_count for trial in trials)} | "
        f"{_token_display(trials, is_reference=runner == 'playwright_reference')} | "
        f"{_cost_display(trials, is_reference=runner == 'playwright_reference')} |"
    )


def _is_open_reference_control(task: ManifestTask, runner: RunnerName) -> bool:
    return (
        runner == "playwright_reference"
        and task.category == "experimental"
        and task.verifier is not None
    )


def _aggregate_row(
    runner: RunnerName,
    records: list[EvidenceRecord],
    verified_records: list[EvidenceRecord],
    skipped: int,
) -> str:
    trials = [record.trial for record in records]
    verified_trials = [record.trial for record in verified_records]
    valid_verified = [trial for trial in verified_trials if trial.outcome != "invalidated"]
    passing = [trial for trial in valid_verified if trial.outcome == "passed"]
    unverified = sum(trial.outcome == "unverified" for trial in trials)
    invalid = sum(trial.outcome == "invalidated" for trial in trials)
    return (
        f"| {RUNNER_LABELS[runner]} | {len(passing)}/{len(valid_verified)} | "
        f"{unverified} | {invalid} | {skipped} | "
        f"{_median_passing_time(passing)} | {sum(trial.usage.request_count for trial in trials)} | "
        f"{_token_display(trials, is_reference=runner == 'playwright_reference')} | "
        f"{_cost_display(trials, is_reference=runner == 'playwright_reference')} |"
    )


def _aggregate_observations(
    manifest: EvaluationManifest,
    grouped: dict[tuple[str, RunnerName], list[EvidenceRecord]],
    by_runner: dict[RunnerName, list[EvidenceRecord]],
) -> list[str]:
    ai_stats: list[tuple[RunnerName, int, int, float | None, int]] = []
    verified_task_ids = {
        task.id for task in manifest.tasks if task.verification_mode == "task_completion"
    }
    for runner in manifest.ai_runners:
        all_trials = [record.trial for record in by_runner[runner]]
        trials = [trial for trial in all_trials if trial.task_id in verified_task_ids]
        valid = [trial for trial in trials if trial.outcome != "invalidated"]
        passing = [trial for trial in valid if trial.outcome == "passed"]
        passing_median = (
            median(trial.duration_ms for trial in passing) / 1_000 if passing else None
        )
        tokens = sum(
            (trial.usage.prompt_tokens or 0) + (trial.usage.completion_tokens or 0)
            for trial in all_trials
        )
        ai_stats.append((runner, len(passing), len(valid), passing_median, tokens))

    best_rate = max(passes / valid if valid else -1 for _, passes, valid, _, _ in ai_stats)
    reliability_leaders = [
        f"{RUNNER_LABELS[runner]} ({passes}/{valid})"
        for runner, passes, valid, _, _ in ai_stats
        if valid and passes / valid == best_rate
    ]
    timed = [item for item in ai_stats if item[3] is not None]
    fastest = min(timed, key=lambda item: item[3] or float("inf")) if timed else None
    timing_note = "- No successful verified AI trials; passing-time comparison is unavailable."
    if fastest is not None:
        timing_note = (
            f"- Lowest median duration among successful AI trials: {RUNNER_LABELS[fastest[0]]} "
            f"({fastest[3]:.3f}s). This is not a like-for-like speed ranking when runners fail "
            "different task mixes."
        )
    fewest_tokens = min(ai_stats, key=lambda item: item[4])
    lines = [
        f"- Highest observed AI success rate: {', '.join(reliability_leaders)}.",
        timing_note,
        f"- Lowest reported AI token consumption: {RUNNER_LABELS[fewest_tokens[0]]} "
        f"({fewest_tokens[4]:,} tokens across all its attempts).",
    ]

    unavailable_cost_runners = []
    for runner in manifest.ai_runners:
        trials = [record.trial for record in by_runner[runner]]
        if any(trial.usage.cost_usd is None for trial in trials):
            unavailable_cost_runners.append(RUNNER_LABELS[runner])
    if unavailable_cost_runners:
        lines.append(
            "- A complete cost ranking is unavailable because cost was not reported for "
            f"{', '.join(unavailable_cost_runners)}."
        )

    reference_failures: list[str] = []
    for task in manifest.tasks:
        trials = [record.trial for record in grouped[(task.id, "playwright_reference")]]
        reference_failure_count = sum(
            trial.outcome not in {"passed", "unverified"} for trial in trials
        )
        if reference_failure_count:
            reference_failures.append(
                f"{_task_label(task)} ({reference_failure_count}/{len(trials)})"
            )
    if reference_failures:
        lines.append(
            "- Deterministic-reference failures require separate inspection and are potential "
            f"site or harness confounds: {', '.join(reference_failures)}."
        )

    for runner in manifest.ai_runners:
        runner_failures: list[str] = []
        for task in manifest.tasks:
            trials = [record.trial for record in grouped[(task.id, runner)]]
            failed = sum(
                trial.outcome not in {"passed", "unverified", "invalidated"}
                for trial in trials
            )
            if failed:
                runner_failures.append(f"{_task_label(task)} ({failed}/{len(trials)})")
        if runner_failures:
            lines.append(
                f"- Observed {RUNNER_LABELS[runner]} failures: "
                f"{', '.join(runner_failures)}."
            )
    return lines


def _median_passing_time(trials: list[TrialEvidence]) -> str:
    if not trials:
        return "—"
    return f"{median(trial.duration_ms for trial in trials) / 1_000:.3f}s"


def _token_display(trials: list[TrialEvidence], *, is_reference: bool) -> str:
    if is_reference:
        return "—"
    known = sum(
        (trial.usage.prompt_tokens or 0) + (trial.usage.completion_tokens or 0)
        for trial in trials
    )
    unavailable = sum(
        trial.usage.prompt_tokens is None or trial.usage.completion_tokens is None
        for trial in trials
    )
    return f"{known:,}" if unavailable == 0 else f"{known:,} + {unavailable} unavailable"


def _cost_display(trials: list[TrialEvidence], *, is_reference: bool) -> str:
    if is_reference:
        return "—"
    known = sum(trial.usage.cost_usd or 0 for trial in trials)
    unavailable = sum(trial.usage.cost_usd is None for trial in trials)
    if unavailable == len(trials):
        return f"unavailable ({unavailable} trials)"
    return f"{known:.8f}" if unavailable == 0 else f"{known:.8f} + {unavailable} unavailable"


def _text_or_unavailable(value: str | None) -> str:
    return value or "unavailable"


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a manifested repeated evaluation report")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(write_repeated_report(manifest_path=args.manifest, output_path=args.output))


if __name__ == "__main__":
    main()
