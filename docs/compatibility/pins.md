# Browser Evaluation Candidate Pins

> Status: approved dependencies installed locally on 2026-08-24. No MCP server,
> model request, browser launch or public-site interaction has run.

Resolved from public package registries and upstream license files. Installation
remains limited to local dependency and browser artifacts; integration runtime
is still approval-bound.

| Component | Candidate version | License | Runtime requirement | Source |
|---|---:|---|---|---|
| `browser-use` | `0.13.8` | MIT | Python `>=3.11,<4.0` | PyPI JSON; upstream `LICENSE` |
| Playwright Python | `1.62.0` | Apache-2.0 | Python `>=3.10`; browser download is separate | PyPI JSON |
| `@browserbasehq/stagehand` | `4.0.2` | MIT | Node `>=22.18.0` | npm registry |
| `@playwright/mcp` | `0.0.79` | Apache-2.0 | Node `>=18` | npm registry |

## Local compatibility verified after installation

- Node is `v22.23.2`, satisfying both Node package engine ranges.
- Python imports `browser-use==0.13.8` and `playwright==1.62.0`.
- `npm ci --ignore-scripts` installed Stagehand `4.0.2` and Playwright MCP
  `0.0.79` from the committed package lock.
- Playwright downloaded ARM64 Chrome for Testing `151.0.7922.34` (browser
  revision `1234`), FFmpeg revision `1011`, and Chrome Headless Shell revision
  `1234` for the reference, restricted and MCP arms.
- browser-use 0.13.8 cannot extract DOM state reliably through `cdp-use==1.4.5`
  on Chromium 151 ARM64. Its functional adapter uses isolated Chromium
  `140.0.7339.16`, Playwright browser revision `1187`, downloaded through
  `uvx --from playwright==1.55.0 playwright install chromium`. The Chromium
  executable SHA-256 is
  `1c8b6d67280a4a7131cebaa9f2e92b2e8abc82cd61dea1d0835eb03eb697f4c0`.
  This browser-version difference is mandatory evidence.
- Both browser lines are local headless artifacts; no personal profile is used.

## Preflight obligations before runtime

1. Resolve exact package artifacts and lockfile entries, including hashes where
   available.
2. Verify browser-use, Stagehand and the generic Playwright-MCP loop can all use
   the configured model and provider endpoint and expose comparable usage fields.
3. Verify Playwright Chromium availability for the local ARM64 host before any
   public target visit.
4. Read the relevant telemetry and data-flow settings; disable optional telemetry
   unless the owner explicitly approves it.
5. Present exact browser version/download size, model endpoint, task domains,
   synthetic payload, request maximum and local spend cap for approval.

## Known comparability risk

`@playwright/mcp` currently declares an alpha Playwright dependency that differs
from the PyPI Playwright candidate. The report must record each browser/driver
version and may not attribute any behavioral difference solely to the agent
strategy until compatibility is verified.
