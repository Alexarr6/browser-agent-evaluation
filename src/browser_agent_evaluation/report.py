from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

from browser_agent_evaluation.models import RunnerName, TrialEvidence

RUNNER_LABELS: dict[RunnerName, str] = {
    "playwright_reference": "Deterministic reference",
    "restricted": "Restricted agent",
    "browser_use": "browser-use",
    "playwright_mcp": "Playwright MCP",
}
RUNNER_ORDER: tuple[RunnerName, ...] = tuple(RUNNER_LABELS)
TASK_LABELS = {
    "wikipedia-search": "Wikipedia",
    "mdn-reference": "MDN",
    "selenium-web-form": "Selenium web form",
    "selenium-ajax-labels": "Selenium AJAX labels",
    "selenium-key-events": "Selenium key events",
    "wikipedia-search-en": "Wikipedia (English)",
    "mdn-reference-en": "MDN (English)",
    "selenium-web-form-en": "Selenium web form (English)",
    "selenium-ajax-labels-en": "Selenium AJAX labels (English)",
    "selenium-key-events-en": "Selenium key events (English)",
    "marca-real-madrid-open-en": "Marca Real Madrid (English)",
    "amazon-cheapest-coffee-beans-en": "Amazon cheapest coffee beans (English)",
}


@dataclass(frozen=True)
class SelectedEvidence:
    path: Path
    sha256: str
    trial: TrialEvidence


def load_comparable_evidence(paths: list[Path]) -> list[SelectedEvidence]:
    selected: list[SelectedEvidence] = []
    identities: set[tuple[str, str]] = set()
    for path in paths:
        raw = path.read_bytes()
        envelope = json.loads(raw)
        if not isinstance(envelope, dict):
            raise ValueError(f"evidence is not a JSON object: {path}")
        trial = TrialEvidence.model_validate(
            {key: value for key, value in envelope.items() if key in TrialEvidence.model_fields}
        )
        identity = (trial.task_id, trial.runner)
        if identity in identities:
            raise ValueError(f"duplicate comparable trial: {identity}")
        if trial.task_id not in TASK_LABELS or trial.runner not in RUNNER_LABELS:
            raise ValueError(f"trial is outside the comparison matrix: {identity}")
        if trial.outcome not in {"passed", "failed"}:
            raise ValueError(f"trial outcome is outside the comparison: {identity}")
        if not trial.cleanup_verified:
            raise ValueError(f"trial lacks cleanup evidence: {identity}")
        if trial.outcome == "passed" and (
            not trial.assertion_results or not all(trial.assertion_results.values())
        ):
            raise ValueError(f"passing trial lacks independent assertions: {identity}")
        if trial.runner != "playwright_reference":
            usage = trial.usage
            if (
                usage.unavailable_reason is not None
                or usage.prompt_tokens is None
                or usage.completion_tokens is None
                or usage.cost_usd is None
            ):
                raise ValueError(f"AI trial lacks comparable provider usage: {identity}")
        identities.add(identity)
        selected.append(
            SelectedEvidence(path=path, sha256=hashlib.sha256(raw).hexdigest(), trial=trial)
        )
    selected_tasks = {task for task, _ in identities}
    expected = {(task, runner) for task in selected_tasks for runner in RUNNER_LABELS}
    if identities != expected:
        missing = sorted(expected - identities)
        raise ValueError(f"comparison matrix is incomplete: {missing}")
    return selected


def render_comparison_report(
    evidence: list[SelectedEvidence],
    *,
    known_total_spend_usd: float,
    unknown_cost_reservations: int,
    reservation_usd: float,
) -> str:
    trials = {(item.trial.task_id, item.trial.runner): item.trial for item in evidence}
    task_ids = [task_id for task_id in TASK_LABELS if any(key[0] == task_id for key in trials)]
    by_runner: dict[str, list[TrialEvidence]] = defaultdict(list)
    for item in evidence:
        by_runner[item.trial.runner].append(item.trial)
    success_summary = "; ".join(
        f"{RUNNER_LABELS[runner]} "
        f"{sum(item.outcome == 'passed' for item in by_runner[runner])}/{len(task_ids)}"
        for runner in RUNNER_ORDER
    )
    lines = [
        f"# Exploratory browser-agent comparison: {len(task_ids)} public tasks",
        "",
        "The deterministic reference is a correctness and site-health baseline, not an "
        "AI-capability baseline. Observed valid success was: " + success_summary + ".",
        "",
        "> This is an exploratory n=1 result per task and runner. It does not establish "
        "population-level reliability or performance.",
        "",
        "## Per-task results",
        "",
        "| Task | Runner | Outcome | Time (s) | Actions | Requests | Input | Output | Total | Cost (USD, approximate) |",  # noqa: E501
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for task_id in task_ids:
        for runner in RUNNER_ORDER:
            trial = trials[(task_id, runner)]
            usage = trial.usage
            input_tokens = "—" if usage.prompt_tokens is None else f"{usage.prompt_tokens:,}"
            output_tokens = (
                "—" if usage.completion_tokens is None else f"{usage.completion_tokens:,}"
            )
            total_tokens = (
                "—"
                if usage.prompt_tokens is None or usage.completion_tokens is None
                else f"{usage.prompt_tokens + usage.completion_tokens:,}"
            )
            cost = "—" if usage.cost_usd is None else f"{usage.cost_usd:.8f}"
            lines.append(
                f"| {TASK_LABELS[task_id]} | {RUNNER_LABELS[runner]} | {trial.outcome} | "
                f"{trial.duration_ms / 1000:.3f} | {trial.action_count} | "
                f"{usage.request_count} | {input_tokens} | {output_tokens} | "
                f"{total_tokens} | {cost} |"
            )

    lines.extend(
        [
            "",
            "## Selected-task aggregate",
            "",
            "| Runner | Success | Mean passing time (s) | All requests | Input | "
            "Output | Total | Cost (USD, approximate) |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for runner in RUNNER_ORDER:
        runner_trials = by_runner[runner]
        passing_trials = [item for item in runner_trials if item.outcome == "passed"]
        total_requests = sum(item.usage.request_count for item in runner_trials)
        token_values = [
            (item.usage.prompt_tokens or 0) + (item.usage.completion_tokens or 0)
            for item in runner_trials
        ]
        costs = [item.usage.cost_usd for item in runner_trials]
        total_input_tokens = sum(item.usage.prompt_tokens or 0 for item in runner_trials)
        total_output_tokens = sum(item.usage.completion_tokens or 0 for item in runner_trials)
        input_tokens = "—" if runner == "playwright_reference" else f"{total_input_tokens:,}"
        output_tokens = "—" if runner == "playwright_reference" else f"{total_output_tokens:,}"
        total_tokens = "—" if runner == "playwright_reference" else f"{sum(token_values):,}"
        total_cost = (
            "—"
            if runner == "playwright_reference"
            else f"{sum(cost for cost in costs if cost is not None):.8f}"
        )
        mean_time = (
            f"{mean(item.duration_ms for item in passing_trials) / 1000:.3f}"
            if passing_trials
            else "—"
        )
        lines.append(
            f"| {RUNNER_LABELS[runner]} | {len(passing_trials)}/{len(task_ids)} | "
            f"{mean_time} | {total_requests} | {input_tokens} | "
            f"{output_tokens} | {total_tokens} | {total_cost} |"
        )

    conservative_total = known_total_spend_usd + unknown_cost_reservations * reservation_usd
    lines.extend(
        [
            "",
            "## What the pilot supports",
            "",
            "- The restricted DSL is project-owned and intentionally less expressive; its selected "
            "failures remain visible rather than being replaced by retries.",
            "- Playwright MCP is viable with Luna when observation is controller-owned and "
            "optional empty page titles are handled by the evidence parser.",
            "- browser-use is viable only with the disclosed OpenRouter structured-output adapter, "
            "exact controller-owned start URL and Chromium 140 compatibility line on ARM64.",
            "- Deterministic Playwright remains the appropriate correctness and site-health "
            "reference, not a substitute for evaluating agent planning.",
            "",
            "## Limits and confounds",
            "",
            "- One selected run per task and runner; no variance or reliability estimate is "
            "possible.",
            "- browser-use used Chromium 140; the other arms used Chromium 151.",
            "- MCP used Playwright MCP 0.0.79 with an alpha Playwright driver and controller-owned "
            "snapshots; browser-use used a project-owned model adapter.",
            "- Action counts are framework-native and not directly equivalent. Setup navigation "
            "is controller-owned in MCP but can appear as an agent action elsewhere.",
            "- Stagehand is excluded because its standard model and tracing contracts do not meet "
            "the approved OpenRouter/privacy configuration.",
            "- Selected failed trials remain in the matrix. Superseded harness diagnostics remain "
            "outside it but still count toward adapter complexity and total spend.",
            "",
            "## Cost boundary",
            "",
            f"Known pilot-wide provider spend is USD {known_total_spend_usd:.8f}. "
            f"{unknown_cost_reservations} responses without captured cost reserve "
            f"USD {reservation_usd:.2f} each, producing a conservative total of "
            f"USD {conservative_total:.8f} against the USD 5.00 cap.",
            "",
            "## Evidence manifest",
            "",
            "| Task | Runner | Evidence | SHA-256 |",
            "|---|---|---|---|",
        ]
    )
    for item in sorted(evidence, key=lambda value: (value.trial.task_id, value.trial.runner)):
        lines.append(
            f"| {TASK_LABELS[item.trial.task_id]} | {RUNNER_LABELS[item.trial.runner]} | "
            f"`{item.path.name}` | `{item.sha256}` |"
        )
    if any(task_id.startswith("selenium-") for task_id in task_ids):
        next_decision = (
            "The matrix now covers read-only navigation, long form submission, repeated AJAX "
            "cycles and keyboard events. Repetitions remain pending; this report must not be "
            "treated as a reliability estimate."
        )
    else:
        next_decision = (
            "The Selenium suite requires separate approval after confirming each exact public "
            "endpoint, method and harmless payload."
        )
    lines.extend(["", "## Next decision", "", next_decision, ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a bounded browser-agent comparison")
    parser.add_argument("evidence", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--known-spend", required=True, type=float)
    parser.add_argument("--unknown-reservations", type=int, default=0)
    parser.add_argument("--reservation-usd", type=float, default=0.25)
    args = parser.parse_args()
    report = render_comparison_report(
        load_comparable_evidence(args.evidence),
        known_total_spend_usd=args.known_spend,
        unknown_cost_reservations=args.unknown_reservations,
        reservation_usd=args.reservation_usd,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
