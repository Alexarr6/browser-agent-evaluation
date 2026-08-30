# Framework Compatibility Decision

## Playwright MCP: included with a shared browser executable

The installed `@playwright/mcp==0.0.79` CLI supports `--executable-path`,
`--headless`, `--isolated` and `--block-service-workers`. The MCP arm can therefore use the same Playwright-installed Chromium 151
executable as the Python reference and restricted-agent arms. browser-use is a
disclosed exception on Chromium 140 because its pinned CDP stack is not functional
with Chromium 151 on ARM64.

Its bundled Playwright driver remains `1.63.0-alpha-2026-08-05`, while the
Python arms use `1.62.0`. This is an architectural/tool-protocol confound, but
not a browser-binary confound when `--executable-path` is enforced. Evidence
must record both driver versions and must not attribute performance differences
solely to planning strategy.

The live MCP pilot also exposed schema-level ambiguity: Luna treated optional
`browser_snapshot.target` as a page URL, while MCP interprets it as a CSS selector.
The bounded adapter therefore hides snapshot along with all JavaScript, file,
screenshot and network-inspection tools. The controller supplies an in-memory
accessibility snapshot after setup, after every model action and for final
acceptance. This changed Wikipedia from a six-request failure dominated by four
snapshot decisions to a two-request pass. MDN also passed in three requests. The
superseded failure remains evidence of the raw tool-protocol cost.

## Stagehand: deferred from the cost-comparable pilot

Stagehand 4.0.2 can receive a local `browserCdpUrl`, and its standard
`ModelConfig` can represent the currently selected direct OpenAI provider. Provider
identity is therefore no longer a reason to exclude it from a future comparison.

The package also requires a telemetry trace object and its default OTLP endpoint
is `https://example.com/v1/traces`; the inspected schema exposes no false/off
mode. Letting it run unchanged could create outbound trace traffic and make data
flow and latency incomparable.

A local trace sink or another verified telemetry-disable mechanism may be
technically possible. It would be a new integration to design, test and approve,
not an out-of-the-box framework comparison. Stagehand remains deferred so the
current comparison stays controlled and interpretable.
