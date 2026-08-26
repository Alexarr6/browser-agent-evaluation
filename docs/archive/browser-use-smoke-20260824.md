# browser-use Wikipedia Smoke Test

## Result

The approved single-run smoke test reached OpenRouter through the installed
`browser-use==0.13.8` adapter and the capture transport recorded provider data:

```text
request_count: 1
prompt_tokens: 5952
completion_tokens: 92
cost_usd: 0.00159825
```

The agent then reported a model connection/response-handling failure and did not
complete the task. This is not a comparable successful trial.

## Safety observation

browser-use downloaded its default browser extensions at startup despite the
local Chromium configuration. The runner now sets `enable_default_extensions=False`.
No later browser-use trial may start until that setting is verified and its model
response handling is adapted to the OpenRouter model's supported output mode.

A second smoke test set `dont_force_structured_output=True` and added the schema
prompt, but browser-use still reported a model-response handling failure after
OpenRouter returned provider usage (6,127 prompt tokens, 190 completion tokens,
USD 0.00175960). It did not download extensions on this second launch.

## Resolution

The owner confirmed browser-use is a mandatory arm. A project-owned
`BaseChatModel` adapter now uses OpenRouter `json_object`, injects browser-use's
dynamic schema, validates locally, and captures provider-reported usage. The
capture transport also removes stale compression headers after observing a
response.

Chromium 151 ARM64 proved incompatible with browser-use's pinned
`cdp-use==1.4.5` DOM/navigation runtime. An isolated browser-use browser line now
uses Chromium `140.0.7339.16` (Playwright revision `1187`). Model-generated
JavaScript and file/PDF actions are disabled.

The final Wikipedia trial passed browser-use's result and independent URL/title
assertions in four actions and 16.21 seconds: 33,659 prompt tokens, 618 completion
tokens, four requests and USD 0.00262927.

The browser session was reset and closed. No MCP server, Stagehand runtime or
Selenium interaction was started.
