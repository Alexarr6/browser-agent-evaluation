# Browser-Agent Evaluation Laboratory

A controlled, evidence-first laboratory for comparing how different browser-agent
architectures solve the same public, non-authenticated tasks.

The project focuses on the trade-offs that a simple pass/fail leaderboard hides:
reliability, end-to-end latency, model usage, operational cost, browser actions, safety
boundaries, and failure modes. It compares a project-owned restricted agent,
[`browser-use`](https://github.com/browser-use/browser-use), Playwright MCP, and a
deterministic Playwright reference under shared task contracts.

> **Research status:** this is an exploratory evaluation harness, not a production
> benchmark or a claim that one framework is universally better. `passed` is reserved
> for contracts whose configured checks verify task completion. A successful
> reachability-only probe is recorded as `unverified`, never as a completed task. See
> [Evaluation criteria and warnings](#evaluation-criteria-and-warnings) before
> interpreting results.

## What this project explores

- How reliably each agent reaches a verifiable browser state.
- How much time, how many model requests, and how many tokens it uses.
- How agent architecture and observation mode affect efficiency and failure recovery.
- How much control can be retained through domain allowlists, bounded actions, fresh
  profiles, explicit budgets, and sanitized evidence.
- Which failures belong to the agent, the provider, the website, or the evaluation
  harness itself.

## Compared approaches

| Runner | Role | Browser interaction |
|---|---|---|
| Deterministic Playwright reference | Site-health and task-contract baseline; no model | Project-owned Playwright recipe |
| Restricted agent | Project-owned agent with a deliberately small action DSL | Semantic actions over an accessibility-oriented DOM |
| `browser-use` | Third-party autonomous browser-agent framework | Framework-owned browser and observations |
| Playwright MCP | Model-driven agent using Playwright's MCP tools | Accessibility snapshots and bounded MCP tools |

The deterministic reference is not an AI competitor or a performance target. On standard
tasks it is a scripted correctness control. On verifier-backed open tasks it uses privileged,
site-specific discovery logic only to check current site and verifier feasibility; those
outcomes are excluded from solution denominators and agent rankings. AI runners still execute
when the manifested reference policy says `always run AI`. Stagehand is available only as a
preflight adapter and is not part of the comparable live matrix.

## How an evaluation works

Each task is a versioned YAML contract containing:

- a start URL and natural-language instruction;
- allowed domains and submission policy;
- action and time limits;
- one or more machine-checkable acceptance assertions.

For every repetition, the harness uses a seeded random order for tasks and runners:

```text
task YAML + experiment.yaml + local .env
                    |
                    v
        deterministic reference trial
                    |
          site-health result
                    |
                    v
         randomized AI runners
            |
            v
 independent assertions + usage/cleanup evidence
            |
            v
       one sanitized JSON artifact per trial
```

Every trial gets a fresh browser profile. A shared round budget limits provider spend,
requests, and optionally tokens. Failed trials remain in the evidence and their known
resource consumption is included in aggregate usage. The implementation lives in
[`src/browser_agent_evaluation/evaluation/rounds.py`](src/browser_agent_evaluation/evaluation/rounds.py).

## Evaluation criteria and warnings

### What is measured

| Dimension | Definition | How to interpret it |
|---|---|---|
| Verified success | The runner reports completion and every assertion in a task-completion contract matches | Primary correctness signal, bounded by assertion coverage |
| Unverified | A reachability-only probe succeeds but cannot prove the full instruction | Never count as a completed task |
| Reliability | Successful valid trials divided by attempted valid trials | Requires repeated runs; an `n=1` result is only exploratory |
| Duration | End-to-end wall-clock time recorded by the runner trial | Operational latency, not isolated model-reasoning time |
| Model usage | Provider-reported prompt tokens, completion tokens, and request count | Includes failed attempts when aggregated |
| Cost | Provider-reported cost, or a documented model-price estimate where supported; otherwise marked unavailable or reserved by the report | Never interpret missing cost as zero |
| Actions | Framework-native browser action count | Diagnostic only; action semantics differ between runners |
| Validity | Cleanup succeeded and evidence satisfies the comparison contract | Invalidated trials are reported separately from ordinary failures |

Acceptance assertions currently support final-page title, URL substring, visible-text
substring, and input-value checks. They are evaluated independently of the model's
natural-language answer. A pass is therefore an **end-state verification**, not a full
trajectory proof or an LLM-as-judge score.

### Important warnings

1. **Assertion coverage is intentionally narrow.** Some task instructions are richer
   than their current assertions. For example, the AJAX task checks the final
   `Lovelace` text but not the complete two-label history, and the keyboard task checks
   for a visible `change` event but not every key in the sequence.

2. **Read experimental results against their recorded contract version.**
   The published run used broad URL/text probes, whose positive outcomes remain
   `unverified`. New runs verify Marca's visible headline and final article URL;
   Amazon now requires a coffee-bean product with a displayed unit price strictly below
   14 EUR/kg and matching name, URL and price in the response. All four runners use the
   same independent checks. The two tasks remain mandatory. Details and the selective
   rerun command are documented in
   [`docs/architecture/open-task-verification.md`](docs/architecture/open-task-verification.md).

3. **Public websites are moving targets.** Consent dialogs, localization, content,
   anti-bot behavior, network conditions, and DOM structure can change between runs.
   A failure can originate in the site, provider, browser, policy, harness, or agent.
   Inspect the evidence before attributing it to planning quality.

4. **Browser compatibility requirements can differ between frameworks.** `browser-use`
   0.13.8 targets its compatible Chromium 140 line on ARM64, while the project-owned
   Playwright stack can target a newer line. The run manifest records the binaries that
   were actually used; both browser paths in the latest run reported Chromium
   140.0.7339.16. Trial duration also includes runner-specific startup and teardown, so
   it measures operational latency rather than a pure model-speed contest.

5. **Equal models do not mean equal model inputs.** All AI runners can use the same
   provider and model, but prompts, tool schemas, context growth, observation formats,
   and framework-owned retries differ by design. Token counts are meaningful system
   costs, but not a direct measure of model intelligence.

6. **Small samples do not establish general reliability.** Use multiple repetitions,
   disclose the exact task set and limits, and report dispersion as well as aggregate
   success. Do not generalize these tasks to authenticated, high-risk, or arbitrary web
   automation.

7. **A reference failure is a confound, not an automatic veto.** By default, all AI
   runners still execute so that every task remains in the matrix. The optional
   `--skip-ai-on-reference-failure` mode protects a constrained diagnostic budget; its
   skipped cells are reported separately and are not AI failures or successes.

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

## Run a live evaluation

Copy the local runtime template and provide browser paths and approved provider
credentials. Never commit `.env`:

```bash
cp runtime.env.example .env
```

The two browser paths are required because `browser-use` 0.13.8 uses a separate
Chromium compatibility line. On macOS, Playwright normally stores binaries under
`~/Library/Caches/ms-playwright/.../chrome-mac/Chromium.app/Contents/MacOS/Chromium`;
on Linux, paths normally use
`~/.cache/ms-playwright/.../chrome-linux/chrome`.

The default English matrix contains five standard tasks and two experimental tasks:

- Wikipedia search
- MDN CSS reference
- Selenium web form
- Selenium AJAX labels
- Selenium keyboard events
- Experimental: Marca Real Madrid article search
- Experimental: Amazon coffee beans below 14 EUR/kg

Run one visual-parity repetition for all three AI runners:

```bash
DISPLAY=:99 UV_CACHE_DIR=/tmp/uv-cache \
uv run browser-eval repeat \
  --repetitions 1 \
  --task-language en \
  --runners restricted browser_use playwright_mcp \
  --model gpt-5.6-luna \
  --max-total-usd 2.00 \
  --max-trial-usd 0.25 \
  --rendering-profile visual-parity \
  --output-dir runs/example-visual-parity
```

Use a new output directory for every run. The CLI prints per-round progress and writes
one sanitized evidence artifact per attempted trial. Raw run directories are ignored
by Git.

Live runs require explicit operator approval. They spend money, consume provider
quota, and interact with public websites. The Amazon task is now read-only: search,
open a product and report its name and unit price. Cart additions, login, checkout,
payment, ordering and personal data are prohibited.

### Provider boundary

The harness is provider-neutral at its configuration boundary. `experiment.yaml`
currently selects an OpenAI-compatible endpoint, credential environment variable, and
one common model for every AI runner. Runner, task, policy, and evidence contracts do
not contain gateway-specific behavior. The current transport contract is the Chat
Completions API.

Use `--model` to override the common model for all AI runners. The older
`--browser-use-model` spelling remains temporarily as a command-line alias.

### Rendering profiles

- `strict` blocks cross-origin assets where supported and preserves the most
  restrictive network behavior.
- `visual-parity` permits passive CSS, image, font, and script resources needed for
  realistic rendering while keeping navigation and tool capabilities bounded.

For a headed run on a host with an X display, set `DISPLAY` (for example,
`DISPLAY=:99`). The project does not manage a VNC server. Do not use a personal browser
profile.

## Safety boundaries

- Every trial uses an isolated, fresh browser profile.
- Navigation is restricted to task allowlists.
- Credentials, arbitrary JavaScript, file access, uploads, downloads, and checkout
  actions are disabled or rejected.
- Task execution is capped at 300 seconds and 48 actions by the current task contracts.
- MCP additionally caps individual actions at 60 seconds and navigation at 90 seconds.
- Budgets can cap total spend, per-trial spend, requests, and cumulative tokens.
- Traces are redacted and bounded before evidence is written.

These controls reduce risk; they do not turn the harness into a sandbox suitable for
untrusted tasks or high-impact browser automation.

## Results and evidence

The current sanitized report lives under [`docs/results/`](docs/results/). Read it with
its recorded date, model, task matrix, runtime limits, browser versions, and known
confounds. Its results are not guarantees about future code or live websites.

### Latest repeated run

The [7 September 2026 report](docs/results/english-repeated-20260907.md) covers all seven
tasks with three repetitions per runner in headless, visual-parity mode using
`gpt-5.6-luna`.

| AI runner | Verified success | Unverified probes | Median verified time | Requests | Tokens | Known cost |
|---|---:|---:|---:|---:|---:|---:|
| `browser-use` | 15/15 | 5 | 23.579s | 152 | 1,659,451 | Unavailable for all trials |
| Playwright MCP | 15/15 | 3 | 12.889s | 142 | 2,224,404 | $0.23690940 |
| Restricted agent | 14/15 | 0 | 21.343s | 120 | 273,315 | $0.10838136 |

These are observed system-level outcomes, not a universal ranking. The deterministic
reference verified 15/15 standard trials and reached both experimental sites 6/6 times;
those probes are not task successes. The report also discloses the reference-only
Wikipedia locale repair and the retrospective reclassification of weak experimental
passes. Read its per-task table, execution notes and warnings before sharing the figures.

After a completed run, render its manifested report with:

```bash
uv run browser-eval report \
  --manifest runs/example-visual-parity/run-manifest.json \
  --output docs/results/english-repeated-YYYYMMDD.md
```

Raw traces, screenshots, provider responses, and generated run directories remain
local. A comparable report should:

- include passed, unverified and failed valid trials;
- distinguish unverified, failed, invalidated, timed-out, and policy-denied outcomes;
- include failed-run time, tokens, requests, and known cost in consumption totals;
- label missing usage or cost rather than converting it to zero;
- disclose task selection, repetitions, model, browser versions, budgets, and rendering
  profile;
- preserve enough sanitized evidence to audit the conclusion.

## Repository layout

```text
src/browser_agent_evaluation/     Python package and CLI
  cli/                            Command parsing and dispatch
  evaluation/                     Trials, task loading, and randomized rounds
  agents/                         Runner-specific planning and execution
  browser/                        Browser isolation and Playwright primitives
  core/                           Task, policy, assertion, budget, and evidence models
  reporting/                      Sanitized evidence and Markdown reports
tasks/                            Standard and experimental task contracts
tests/                            Offline unit and contract tests
docs/architecture/                Package boundaries and design notes
docs/compatibility/               Framework and browser compatibility decisions
docs/results/                     Current sanitized evaluation report
experiment.yaml                  Default local experiment configuration
runtime.env.example              Safe environment template
pyproject.toml / uv.lock         Python dependencies and tooling
package.json / package-lock.json Pinned Node adapters
```

The public entry point is `browser-eval`, defined in `pyproject.toml` and dispatched by
[`src/browser_agent_evaluation/cli/main.py`](src/browser_agent_evaluation/cli/main.py).
The package architecture and dependency direction are documented in
[`docs/architecture/package-structure.md`](docs/architecture/package-structure.md), and
[`docs/README.md`](docs/README.md) is the complete documentation index.

## Development

For code changes, run the complete offline suite:

```bash
uv run pytest
uv run ruff check .
uv run mypy src
```

Do not add live model or public-site execution to CI. Live evaluations belong to an
explicitly approved local run and must use a fresh output directory.

Dependency changes must update and review the relevant lockfile:

```bash
uv lock
npm install --package-lock-only
```

Generated evidence policy:

- Commit only selected Markdown reports useful for understanding the experiment.
- Do not commit raw traces, screenshots, provider responses, credentials, browser
  profiles, or large generated result directories.
- Reports must state their date, task matrix, model, browser versions, limits, and known
  confounds.
- Historical preflight and diagnostic notes under `docs/archive/` are not current
  runtime guarantees.

## License

This repository is published without an open-source license. All rights reserved. The
third-party packages used by the experiment retain their own licenses.
