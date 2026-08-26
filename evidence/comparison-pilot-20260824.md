# Exploratory browser-agent comparison: 5 public tasks

The deterministic reference is a correctness and site-health baseline, not an AI-capability baseline. Observed valid success was: Deterministic reference 5/5; Restricted agent 3/5; browser-use 4/5; Playwright MCP 5/5.

> This is an exploratory n=1 result per task and runner. It does not establish population-level reliability or performance.

## Per-task results

| Task | Runner | Outcome | Time (s) | Actions | Requests | Tokens | Cost (USD) |
|---|---|---:|---:|---:|---:|---:|---:|
| Wikipedia | Deterministic reference | passed | 1.299 | 3 | 0 | — | — |
| Wikipedia | Restricted agent | passed | 7.873 | 1 | 2 | 3,882 | 0.00126310 |
| Wikipedia | browser-use | passed | 16.210 | 4 | 4 | 34,277 | 0.00262927 |
| Wikipedia | Playwright MCP | passed | 9.065 | 1 | 2 | 8,733 | 0.00172573 |
| MDN | Deterministic reference | passed | 1.192 | 2 | 0 | — | — |
| MDN | Restricted agent | passed | 6.756 | 1 | 2 | 4,109 | 0.00125100 |
| MDN | browser-use | passed | 18.462 | 5 | 4 | 37,865 | 0.00358612 |
| MDN | Playwright MCP | passed | 12.339 | 2 | 3 | 23,588 | 0.00363546 |
| Selenium web form | Deterministic reference | passed | 0.763 | 8 | 0 | — | — |
| Selenium web form | Restricted agent | failed | 39.795 | 0 | 3 | 3,370 | 0.00103400 |
| Selenium web form | browser-use | passed | 36.516 | 9 | 9 | 76,337 | 0.00575397 |
| Selenium web form | Playwright MCP | passed | 18.380 | 7 | 8 | 30,668 | 0.00243002 |
| Selenium AJAX labels | Deterministic reference | passed | 12.438 | 7 | 0 | — | — |
| Selenium AJAX labels | Restricted agent | failed | 22.396 | 4 | 5 | 5,480 | 0.00175700 |
| Selenium AJAX labels | browser-use | passed | 30.482 | 7 | 7 | 55,760 | 0.00358066 |
| Selenium AJAX labels | Playwright MCP | passed | 24.065 | 6 | 7 | 10,593 | 0.00138936 |
| Selenium key events | Deterministic reference | passed | 0.410 | 8 | 0 | — | — |
| Selenium key events | Restricted agent | passed | 29.752 | 7 | 8 | 9,265 | 0.00341320 |
| Selenium key events | browser-use | failed | 15.474 | 0 | 1 | 8,673 | 0.00167648 |
| Selenium key events | Playwright MCP | passed | 16.047 | 7 | 8 | 10,151 | 0.00119525 |

## Selected-task aggregate

| Runner | Success | Mean passing time (s) | All requests | All tokens | All cost (USD) |
|---|---:|---:|---:|---:|---:|
| Deterministic reference | 5/5 | 3.220 | 0 | — | — |
| Restricted agent | 3/5 | 14.794 | 20 | 26,106 | 0.00871830 |
| browser-use | 4/5 | 25.418 | 25 | 212,912 | 0.01722650 |
| Playwright MCP | 5/5 | 15.979 | 28 | 83,733 | 0.01037582 |

## What the pilot supports

- The restricted DSL is project-owned and intentionally less expressive; its selected failures remain visible rather than being replaced by retries.
- Playwright MCP is viable with Luna when observation is controller-owned and optional empty page titles are handled by the evidence parser.
- browser-use is viable only with the disclosed OpenRouter structured-output adapter, exact controller-owned start URL and Chromium 140 compatibility line on ARM64.
- Deterministic Playwright remains the appropriate correctness and site-health reference, not a substitute for evaluating agent planning.

## Limits and confounds

- One selected run per task and runner; no variance or reliability estimate is possible.
- browser-use used Chromium 140; the other arms used Chromium 151.
- MCP used Playwright MCP 0.0.79 with an alpha Playwright driver and controller-owned snapshots; browser-use used a project-owned model adapter.
- Action counts are framework-native and not directly equivalent. Setup navigation is controller-owned in MCP but can appear as an agent action elsewhere.
- Stagehand is excluded because its standard model and tracing contracts do not meet the approved OpenRouter/privacy configuration.
- Selected failed trials remain in the matrix. Superseded harness diagnostics remain outside it but still count toward adapter complexity and total spend.

## Cost boundary

Known pilot-wide provider spend is USD 0.07549466. 6 responses without captured cost reserve USD 0.25 each, producing a conservative total of USD 1.57549466 against the USD 5.00 cap.

## Evidence manifest

| Task | Runner | Evidence | SHA-256 |
|---|---|---|---|
| MDN | browser-use | `browser-use-70bf37b2c719.json` | `bace8abfaab9a18934d8a5f0d0822098f0a565b554a110b4e1cccb6493d5181d` |
| MDN | Playwright MCP | `playwright-mcp-7e0733b49e41.json` | `c4ee028af82bc8bb0c95767d42e6f3fd9ce4b4616098c823d139b117a29bca4d` |
| MDN | Deterministic reference | `reference-9176ab8446ec.json` | `d0de39f49a8306703579e5a7f1be444c98474d8f07b5ef12e9d13ba8f2669f0f` |
| MDN | Restricted agent | `restricted-d9dd82a4430d.json` | `404c452fdc62aeae3efe02278533c992e402fb3a56a45cd79c5997780097f747` |
| Selenium AJAX labels | browser-use | `browser-use-c0ed432c5894.json` | `0af3f00e34a751951989209207eba50aa671b765d276fdf12724cf55f06463ce` |
| Selenium AJAX labels | Playwright MCP | `playwright-mcp-ce9cca48af78.json` | `1565696796e45b4c4af49045376624ebf63a520fad19aaea7a1105c034bfe84d` |
| Selenium AJAX labels | Deterministic reference | `reference-ca45c391731c.json` | `47e20b4acdbc96233fa7244ca7bb4a1e85714c2e1dd38ea0b41296d913e8fcc2` |
| Selenium AJAX labels | Restricted agent | `restricted-954d4d5da8ec.json` | `fcd6b94e26eb72682e8771cdd35b1f4c60ab46514e89e8f4f73bf26c4e65cab9` |
| Selenium key events | browser-use | `browser-use-7505a41975c1.json` | `c2ced3656b7a4073946ed999e92c4d7bb577ef423398d0b68b6ad7ad0e3ff51e` |
| Selenium key events | Playwright MCP | `playwright-mcp-2aec63689fd7.json` | `d113d17ff2b582fcb0d9d1bf423e2516d2169545f9006d3c25f684f3a9e41f01` |
| Selenium key events | Deterministic reference | `reference-42a0c748f936.json` | `9fc7aa97e8bcce2736fa4f542c0b79febc443112eb10df2ef8509047ff776dfd` |
| Selenium key events | Restricted agent | `restricted-55c0412321d5.json` | `87805a5e2b043e435b0441dabc3bf119562b5143230f26a5a1a12ddb70c64380` |
| Selenium web form | browser-use | `browser-use-43374f1e3cde.json` | `6aac99d309f77e2988f409003a32bc6d4718f780cba8f42091d6c29a8cbc26e0` |
| Selenium web form | Playwright MCP | `playwright-mcp-ab0bb112d2cc.json` | `a803850a0ec0f8e626de42f3b4a6b9f31657a9bd1e41753217eacbbec89fc1fa` |
| Selenium web form | Deterministic reference | `reference-82fb0e8b4c28.json` | `104ef1ec7dd997d9e5509cc30c9e3eba9729ada2520d91ccd79112c41c614efd` |
| Selenium web form | Restricted agent | `restricted-c749849a8f19.json` | `1f5388081bcb99129c4b180e190cf67731aab91e7c1951474f6894575f8f4cd9` |
| Wikipedia | browser-use | `browser-use-b9c3a320990c.json` | `e33ab856f4bbb4eb3ea7bfde14238e7777c856519f8e3ce7279ce88202cdfc18` |
| Wikipedia | Playwright MCP | `playwright-mcp-24d87cf28d5b.json` | `9a87fad7a118d61a787492e78bb8855b679472796bf6e0cdd026ca3aed0a1522` |
| Wikipedia | Deterministic reference | `reference-f96b28ad0dde.json` | `fff09ff38a55f3bf4ea633a0b531f08c41035fa01902820d1152fad0d6cd5d38` |
| Wikipedia | Restricted agent | `restricted-6b4f3340ac31.json` | `4b187c7536ecc0a6108be6ef973a76a2652b0aca8ca800bf94d8a2f60986f19e` |

## Next decision

The matrix now covers read-only navigation, long form submission, repeated AJAX cycles and keyboard events. Repetitions remain pending; this report must not be treated as a reliability estimate.
