# Repeated-Sample Runtime Hardening

## Scope

This correction prepares a new controlled sample without executing a browser or
model request.

## Corrections

- Playwright MCP normalizes only the alpha driver's exact `ref=eN`
  accessibility-reference spelling to `eN`; arbitrary selectors remain unchanged.
- The browser-use adapter force-kills its session after final observation and
  wraps a post-request failure with captured provider usage, bounded trace and
  cleanup status.
- The repeated-run controller writes failed or invalidated evidence for
  browser-use and MCP failures instead of aborting without an artifact. A failed
  deterministic reference skips only that task's AI arms for the round.
- English task contracts live under `tasks/en/`. They preserve each Spanish
  task's URL, policy, limits, acceptance and deterministic action shape while
  changing only model-visible instruction and completion text. English text is
  ASCII-only.

## Verification

```text
Experiment: 81 tests passed; Ruff and mypy passed; experiment uv lock check passed.
Product: 212 tests passed, 6 approval-gated skips; Ruff and mypy passed; root uv lock check passed.
```

No Chromium, Playwright MCP, Stagehand, browser-use, or model process was
started by this correction.
