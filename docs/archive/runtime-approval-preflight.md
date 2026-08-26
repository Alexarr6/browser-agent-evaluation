# Browser Evaluation Runtime Approval Preflight

**Status:** prepared on 2026-08-24. No browser process, MCP transport or model
request has run.

## Local limits

| Limit | Value |
|---|---:|
| Provider | OpenRouter `https://openrouter.ai/api/v1` |
| Model | `openai/gpt-5.6-luna` |
| Pilot-wide model cap | USD 5.00 (a conservative operational cap for the owner's EUR 5 budget) |
| Per-trial model cap | USD 0.25 |
| Per-trial model requests | 12 |
| AI trial plan | 4 AI arms × 3 tasks × 3 repetitions = 36 trials |
| Browser mode | Headless Chromium, fresh profile per trial |

The harness must stop when the provider does not report comparable usage/cost.
It must not read credentials except the explicitly supplied OpenRouter key at
runtime, and it must redact the key from evidence.

## Proposed public interactions

| Task | Start URL and allowed domains | Procedure | Risk | Required authority |
|---|---|---|---|---|
| Wikipedia search | `https://www.wikipedia.org/`; `www.wikipedia.org`, `en.wikipedia.org` | Search `Playwright`, open the article, verify title `Playwright`. | Read-only | Public navigation only |
| MDN CSS reference | `https://developer.mozilla.org/`; `developer.mozilla.org` | Search CSS selector `:has()`, open its reference, verify visible `:has()`. | Read-only | Public navigation only |
| Selenium test form | `https://www.selenium.dev/selenium/web/web-form.html`; `www.selenium.dev` | Enter `Ada Lovelace`, choose `Two`, check the test box, submit, verify `Received!`. | Synthetic form | Explicit form-submit approval required |

Every task uses a 60-second timeout. Wikipedia and MDN allow at most 12 browser
actions; Selenium allows at most 16. Logins, credentials, downloads, payments,
CAPTCHA bypass, stealth, profiles and irreversible actions remain prohibited.

## Telemetry and comparability gates

1. `browser-use` defaults `ANONYMIZED_TELEMETRY` to true and defaults cloud sync
   from that value. `runtime_environment.py` now forces
   `ANONYMIZED_TELEMETRY=false` and `BROWSER_USE_CLOUD_SYNC=false` for its
   runner process; `runtime.env.example` records the required values.
2. Stagehand 4.0.2 declares an OpenTelemetry trace configuration whose default
   endpoint is `https://example.com/v1/traces`, with no inspected disable switch.
   It also cannot represent the required OpenRouter model/base URL in its standard
   model configuration. Stagehand is deferred from this cost-comparable pilot.
3. Playwright MCP 0.0.79 includes Playwright `1.63.0-alpha-2026-08-05`, while the
   Python deterministic/reference arms use Playwright 1.62.0. Its CLI supports
   `--executable-path`, so the MCP arm will use the same Chromium executable as
   every other included arm. Its driver/tool protocol remains a recorded
   architectural limitation, not a browser-binary difference.

## Approval required before runtime

A runtime authorization must state all of the following:

- whether to run reference-only navigation for the two read-only tasks;
- whether to submit the Selenium synthetic form;
- whether to send requests to the exact OpenRouter endpoint/model under the
  listed USD limits;
- acknowledgement that Stagehand is deferred pending a separately designed
  OpenRouter client and contained tracing adapter; and
- whether to include Playwright MCP with the shared Chromium executable despite
  its alpha driver/tool-protocol limitation.

Without those answers, this preflight is evidence only and execution is blocked.
