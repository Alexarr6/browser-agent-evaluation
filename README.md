# Browser-Agent Evaluation Laboratory

A controlled, reproducible harness for comparing browser-agent strategies on public,
non-authenticated tasks. It evaluates a project-owned restricted agent, `browser-use`,
Playwright MCP, and a deterministic Playwright reference under the same task contracts.

This repository is an experiment, not production application code. It must not be
imported by the LinkedIn presence application.

> **License status:** This repository is published without an open-source license.
> All rights reserved. The third-party packages used by the experiment retain their
> own licenses.

## Quick start

Requirements:

- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/)
- Node.js 22.18+ and npm
- Chromium binaries compatible with the configured browser paths
- An OpenAI-compatible API key for live model runs

Install the locked dependencies:

```bash
uv sync --locked
npm ci --ignore-scripts
```

Run the local, offline validation suite:

```bash
uv run pytest
uv run ruff check .
uv run mypy src
```

These commands do not launch a browser, contact a model provider, or visit a public
site.

## Run an evaluation

Copy the local runtime template and fill in browser paths and the approved provider
credentials. Never commit `.env`:

```bash
cp runtime.env.example .env
```

The default English matrix contains seven tasks:

- Wikipedia search
- MDN CSS reference
- Selenium web form
- Selenium AJAX labels
- Selenium keyboard events
- Marca Real Madrid article search
- Amazon cheapest coffee-beans task

A one-repetition visual-parity run for all three AI arms is:

```bash
DISPLAY=:99 UV_CACHE_DIR=/tmp/uv-cache \
uv run python -m browser_agent_evaluation.repeat_pilot \
  --repetitions 1 \
  --task-language en \
  --runners restricted browser_use playwright_mcp \
  --browser-use-model gpt-5.6-luna \
  --max-total-usd 2.00 \
  --max-trial-usd 0.25 \
  --rendering-profile visual-parity \
  --output-dir runs/example-visual-parity
```

Use a new output directory for every run. Raw run artifacts are intentionally ignored
by Git. The harness prints per-round, per-runner progress and writes sanitized trial
evidence locally.

Live runs require explicit operator approval. They can spend money, consume provider
quota, and interact with public websites. The Amazon task permits only an anonymous
cart addition; it prohibits login, checkout, payment, ordering, and personal data.

## Browser visibility

For headed runs on the local evaluation host:

```bash
DISPLAY=:99
```

The project does not manage a VNC server. If the host provides one, connect to its
configured forwarded port. Do not use a personal browser profile.

## Safety and comparability boundaries

- Every trial uses an isolated, fresh browser profile.
- Navigation is restricted to task allowlists.
- Credentials, arbitrary JavaScript, file access, uploads, downloads, and checkout
  actions are disabled or rejected.
- The default task timeout is capped at 300 seconds.
- MCP has stricter per-operation limits: 60 seconds for actions and 90 seconds for
  navigation.
- `strict` preserves restrictive network behavior; `visual-parity` permits passive
  CSS, image, font, and script resources needed for realistic rendering while keeping
  navigation and tool capabilities bounded.
- `browser-use` uses its documented Chromium 140 compatibility line on ARM64;
  reference, restricted, and MCP use Chromium 151. This is a known comparability
  limitation and must be reported with results.
- Stagehand is present only as a preflight adapter and is not part of the comparable
  live pilot.
- Experimental Amazon acceptance is intentionally exploratory and should not be
  treated as a fully independent product/cost correctness assertion until its
  acceptance contract is strengthened.

## Repository layout

```text
src/browser_agent_evaluation/  Python harness and adapters
tests/                         Offline unit and contract tests
tasks/                         Public task contracts and workflows
evidence/                      Selected, reviewable Markdown reports
docs/                         Design and historical documentation
experiment.yaml                Local experiment configuration
runtime.env.example            Safe environment template
pyproject.toml / uv.lock       Python project and dependency lock
package.json / package-lock.json  Node adapter dependencies and lock
```

Local-only material is deliberately excluded from version control:

- `runs/` raw trial output and traces
- `.env` and other local environment files
- `.venv/`, `node_modules/`, caches, build products, and logs
- generated JSON evidence and screenshots
- Pi/editor/runtime state

## Development practices

Keep changes small and testable. For code changes, run the complete offline suite:

```bash
uv run pytest
uv run ruff check .
uv run mypy src
```

Do not add live model or public-site execution to CI. Live evaluations belong to an
explicitly approved local run and must use a fresh output directory.

Dependency changes must update the relevant lockfile:

```bash
uv lock
npm install --package-lock-only
```

Review the generated lockfile before committing it.

## Evidence policy

Commit only selected Markdown reports that are useful for understanding the experiment.
Do not commit raw traces, screenshots, provider responses, credentials, browser
profiles, or large generated result directories. Reports must be sanitized and should
state their date, task matrix, model, browser versions, limits, and known confounds.

Historical preflight and diagnostic notes live under `docs/archive/`; they describe
past states and are not current runtime guarantees.
