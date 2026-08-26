# Orchestrator smoke evidence — 2026-08-24

This file records the first live evidence produced by the new connector-neutral
workflow orchestrator. It is **not** a fair comparison of connectors and **must not**
be combined with prior English repeated samples or historical Spanish evidence. It
only proves that the orchestrator opens and closes a fresh session per connector,
advances ordered steps with independent acceptance, force-closes on cleanup and
records bounded usage.

## Configuration

```yaml
configuration_sha256: 2493b94585341189f6bcc1a549cf637ad06424ec89aec5b8e43c0f2dcd6e23cb
workflow: wikipedia-search-en (steps: search-playwright, open-article, verify-title)
browser: chromium-1234 (Headless Chromium 151)
model: openai/gpt-5.4-mini
completion_tokens: 30000
max_tokens_per_run: 500000
per_run_cost_cap: 0.07
total_cost_cap: 3.15
```

## Per-connector outcomes

| Connector | Outcome | Passed steps | Failed steps | Acceptance | Provider usage | Notes |
|---|---|---:|---:|---|---|---|
| `playwright_reference` | passed | 3/3 | 0/3 | `page_title: True` | n/a | Reference stub; verifies orchestrator wiring only. |
| `browser_use` | failed | 0/1 | 1/1 | none | 226,823 tokens, USD 0.05026725, 25 requests | Browser session opened; the agent emitted 12 actions, repeatedly landed on `about:blank` and never produced the verify step. The orchestrator correctly stopped after the failed step. |
| `playwright_mcp` | failed | 1/2 | 1/2 | `url_contains` mixed | 0 tokens (provider usage did not reach evidence) | MCP session opened; first step passed by snapshot URL alone, second step failed because the model returned a non-JSON terminal response. Provider usage was not captured because the pilot loop terminated before OpenRouter usage was read. |
| `restricted` | failed | 0/1 | 1/1 | none | n/a | Restricted executor failed inside Playwright: locator `[placeholder='Search Wikipedia']` did not become visible within 30 s, so the first step could not fill the input. |

## Cleanup evidence

- No Chromium/MCP/browser-use/Stagehand process remained after the smoke finished.
- Every connector receipt has `cleanup_verified: true` with the recorded
  `cleanup_detail` ("browser-use force kill completed", "MCP session closed via MCP
  stdio shutdown", "restricted session force-closed").

## Failure modes captured honestly

- **browser-use**: did not finish any of the three workflow steps against the
  single Wikipedia workflow even with 30k output tokens and the budget ceiling
  raised. It spent 25 requests and 226k tokens; the model insisted on repeated
  waits without producing a verifiable Playwright article. This is a real,
  recorded failure, not a workaround.
- **playwright_mcp**: produced valid tool calls and snapshots but the model never
  returned the expected terminal JSON. Provider usage was therefore not captured in
  the step receipt — that is a known telemetry gap, not a successful run.
- **restricted**: failed because the synthetic Playwright selector did not match
  the live Wikipedia input. This is a step-instruction and template gap, not a
  runtime bug.

## What this evidence does and does not prove

- It proves the new orchestrator wires each connector through one persistent
  session, accepts independently of the connector, stops on first failed step,
  verifies forced cleanup and emits versioned receipts with shared
  `configuration_sha256`.
- It does **not** prove the connectors produce comparable, repeatable results.
  Only one repetition per connector was executed and each had a different failure
  mode. Any future repeat must use the same configuration hash and a fresh
  configuration revision.
- Total provider spend: USD 0.05026725.