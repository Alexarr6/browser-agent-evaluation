from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from statistics import median

from browser_agent_evaluation.models import RunnerName, TrialEvidence
from browser_agent_evaluation.report import RUNNER_LABELS, RUNNER_ORDER, TASK_LABELS


class RepeatedReportError(ValueError):
    """Raised when a repeated evidence set is incomplete or non-comparable."""


def load_english_repeated_evidence(paths: list[Path]) -> list[tuple[Path, str, TrialEvidence]]:
    records: list[tuple[Path, str, TrialEvidence]] = []
    trial_ids: set[str] = set()
    for path in paths:
        raw = path.read_bytes()
        envelope = json.loads(raw)
        if not isinstance(envelope, dict):
            raise RepeatedReportError(f"evidence is not an object: {path}")
        trial = TrialEvidence.model_validate(
            {key: value for key, value in envelope.items() if key in TrialEvidence.model_fields}
        )
        if not trial.task_id.endswith("-en"):
            raise RepeatedReportError(f"non-English evidence is outside this report: {path}")
        if trial.trial_id in trial_ids:
            raise RepeatedReportError(f"duplicate trial id: {trial.trial_id}")
        if not trial.cleanup_verified:
            raise RepeatedReportError(f"trial lacks verified cleanup: {path}")
        if (
            trial.runner != "playwright_reference"
            and trial.outcome == "passed"
            and trial.usage.unavailable_reason is not None
        ):
            raise RepeatedReportError(f"passing AI trial lacks provider usage: {path}")
        trial_ids.add(trial.trial_id)
        records.append((path, hashlib.sha256(raw).hexdigest(), trial))

    expected_tasks = {task_id for task_id in TASK_LABELS if task_id.endswith("-en")}
    grouped: dict[tuple[str, RunnerName], list[TrialEvidence]] = defaultdict(list)
    for _, _, trial in records:
        grouped[(trial.task_id, trial.runner)].append(trial)
    expected = {(task_id, runner) for task_id in expected_tasks for runner in RUNNER_ORDER}
    if set(grouped) != expected:
        raise RepeatedReportError("English repeated evidence matrix is incomplete")
    counts = {len(trials) for trials in grouped.values()}
    if counts != {3}:
        raise RepeatedReportError("every task and runner requires exactly three repetitions")
    return records


def render_english_repeated_report(records: list[tuple[Path, str, TrialEvidence]]) -> str:
    grouped: dict[tuple[str, RunnerName], list[TrialEvidence]] = defaultdict(list)
    for _, _, trial in records:
        grouped[(trial.task_id, trial.runner)].append(trial)
    task_ids = [task_id for task_id in TASK_LABELS if task_id.endswith("-en")]
    lines = [
        "# English-only repeated browser-agent evaluation",
        "",
        "This report contains three repetitions for each of seven English task contracts and "
        "four runners. Spanish trials and prior invalidated diagnostics are excluded.",
        "",
        "## Per-task success",
        "",
        "| Task | Runner | Success | Median passing time (s) | All requests | All tokens | "
        "All cost (USD) |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    by_runner: dict[RunnerName, list[TrialEvidence]] = defaultdict(list)
    for task_id in task_ids:
        for runner in RUNNER_ORDER:
            trials = grouped[(task_id, runner)]
            by_runner[runner].extend(trials)
            passing = [trial for trial in trials if trial.outcome == "passed"]
            passing_time = (
                f"{median(trial.duration_ms for trial in passing) / 1_000:.3f}"
                if passing
                else "—"
            )
            tokens = sum(
                (trial.usage.prompt_tokens or 0) + (trial.usage.completion_tokens or 0)
                for trial in trials
            )
            cost = sum(trial.usage.cost_usd or 0 for trial in trials)
            is_reference = runner == "playwright_reference"
            unknown_costs = (
                0 if is_reference else sum(trial.usage.cost_usd is None for trial in trials)
            )
            cost_display = "—" if is_reference else _cost_display(cost, unknown_costs)
            token_display = "—" if is_reference else f"{tokens:,}"
            request_count = sum(trial.usage.request_count for trial in trials)
            lines.append(
                f"| {TASK_LABELS[task_id]} | {RUNNER_LABELS[runner]} | "
                f"{len(passing)}/{len(trials)} | {passing_time} | "
                f"{request_count} | {token_display} | {cost_display} |"
            )

    lines.extend(
        [
            "",
            "## Runner aggregate",
            "",
            "| Runner | Success | Median passing time (s) | All requests | All tokens | "
            "All cost (USD) |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for runner in RUNNER_ORDER:
        trials = by_runner[runner]
        passing = [trial for trial in trials if trial.outcome == "passed"]
        median_time = (
            f"{median(trial.duration_ms for trial in passing) / 1_000:.3f}" if passing else "—"
        )
        tokens = sum(
            (trial.usage.prompt_tokens or 0) + (trial.usage.completion_tokens or 0)
            for trial in trials
        )
        cost = sum(trial.usage.cost_usd or 0 for trial in trials)
        is_reference = runner == "playwright_reference"
        unknown_costs = 0 if is_reference else sum(trial.usage.cost_usd is None for trial in trials)
        cost_display = "—" if is_reference else _cost_display(cost, unknown_costs)
        token_display = "—" if is_reference else f"{tokens:,}"
        request_count = sum(trial.usage.request_count for trial in trials)
        lines.append(
            f"| {RUNNER_LABELS[runner]} | {len(passing)}/{len(trials)} | {median_time} | "
            f"{request_count} | {token_display} | {cost_display} |"
        )

    known_ai_cost = sum(
        trial.usage.cost_usd or 0
        for _, _, trial in records
        if trial.runner != "playwright_reference"
    )
    unknown_ai_costs = sum(
        trial.runner != "playwright_reference" and trial.usage.cost_usd is None
        for _, _, trial in records
    )
    lines.extend(
        [
            "",
            "## Limits",
            "",
            "- This is an English-only, n=3-per-cell exploratory sample including standard and "
            "open-ended tasks; it is not pooled with Spanish tasks and does not establish "
            "general reliability.",
            "- Every AI trial used a 300-second task timeout, 48 action cap, 24 request cap, "
            "50,000 cumulative-token cap and USD 0.07 trial cap.",
            "- browser-use uses its disclosed isolated Chromium 140 line; the other arms use "
            "Chromium 151.",
            "- Failed trials remain in success, token, request and known-cost totals. Each "
            "response without provider cost is explicitly reserved at the USD 0.07 trial cap.",
            f"- Known English-only provider spend: USD {known_ai_cost:.8f}; "
            f"{unknown_ai_costs} unavailable-cost trial(s) reserve "
            f"USD {unknown_ai_costs * 0.07:.2f}.",
            "",
            "## Evidence manifest",
            "",
            "| Trial | Evidence | SHA-256 |",
            "|---|---|---|",
        ]
    )
    for path, sha256, trial in sorted(records, key=lambda item: item[2].trial_id):
        lines.append(f"| {trial.trial_id} | `{path.name}` | `{sha256}` |")
    lines.append("")
    return "\n".join(lines)


def _cost_display(cost: float, unknown_costs: int) -> str:
    return f"{cost:.8f}" if unknown_costs == 0 else f"{cost:.8f} + {unknown_costs} reserve"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render an English-only repeated evaluation report"
    )
    parser.add_argument("evidence", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = render_english_repeated_report(load_english_repeated_evidence(args.evidence))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
