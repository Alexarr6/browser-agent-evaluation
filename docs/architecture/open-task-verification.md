# Verification of real-world tasks

All seven tasks are mandatory. The current Marca and Amazon contracts use
`task_completion` and controller-owned DOM evidence. The older published run retains
its original broad assertions and `unverified` experimental outcomes until refreshed.

## Current acceptance criteria

| Task | Independently observed evidence | Required answer |
|---|---|---|
| Marca | Visible main heading and HTTPS article URL under `/futbol/real-madrid/YYYY/MM/DD/*.html` | JSON `name` and `url` matching the heading and final URL |
| Amazon | Visible product title, Amazon product URL with ASIN, and one unambiguous displayed EUR/kg amount from the product's main price block | JSON `name`, `url`, `eur_per_kg` matching the observed values; unit price strictly between 0 and 14 |

Amazon searches for coffee beans and opens a product from the first results page.
It no longer requires a global minimum, a cart action or a purchase. Its old task ID
`amazon-cheapest-coffee-beans-en` is retained as the replacement slot identifier;
the manifest's contract hash and verifier identify the new task definition.

The verifier reads the visible `h1` on Marca and `#productTitle` plus
`#corePriceDisplay_desktop_feature_div` on Amazon. The same fixed, read-only extraction
is used through Playwright, browser-use and MCP. MCP's evaluate tool remains hidden
from the model. Facts and the runner answer are persisted in `verification_evidence`;
the report replays these checks for new passing artifacts.

The restricted runner returns JSON inside its terminal `result`, browser-use
inside its final response, and MCP inside its terminal `summary`. Restricted and MCP
accept an answer object or its JSON string representation, preserving the supplied
values. MCP allows one terminal-envelope correction within the existing request,
token, cost and time budgets; malformed output is recorded in the trace. Explicit
failure remains failure, and the independent verifier still checks the answer.

Heading comparison normalizes whitespace. URL comparison requires HTTPS and the
correct site: Marca requires the same dated article path; Amazon requires the same
ASIN, accepting `/dp/ASIN`, `/gp/product/ASIN` and product-slug links. Tracking queries,
fragments and the optional `www` prefix do not affect identity. Different ASINs,
articles and off-site links fail. Amazon accepts decimal
commas or decimal points in displayed prices; 14.00 EUR/kg fails. Conflicting unit
prices, missing evidence, mismatched answers and non-product pages cannot pass.
Missing required checks count as failed acceptance in the new contracts. Legacy
reachability-only contracts remain `unverified` when their limited checks succeed.

These are bounded final-state checks. They do not independently prove every navigation
step or cookie choice. Marca's section URL is the operational definition of a Real
Madrid article; it does not semantically judge its entire body. Amazon uses the main
displayed unit price, not a guarantee of checkout price or continued availability.
DOM changes or absent main price blocks can produce false negatives.

The Amazon policy explicitly permits Enter on the named Amazon search field while
keeping general form submission disabled. Restricted and MCP normalize the case of
named keys such as Enter, Home and End without changing typed characters. No tools,
navigation retries or action/time budgets were added to resolve poor agent choices.
The deterministic reference uses privileged, site-specific recipes and is a
site/verifier control, not a general solution to an open instruction. Its Marca and Amazon
outcomes must be reported as control checks and excluded from solution denominators and agent
rankings. A changing news section or product layout can invalidate that recipe even when another
strategy remains viable. For that reason, failure of a verifier-backed open-task control never
skips the AI agent attempts, even when reference-failure skipping is enabled for standard tasks.
A single pilot repetition checks integration; it does not establish a reliable ranking of agents.

The initial `open-tasks-check-20260907` pilot predates these adapter and URL changes.
Its artifacts retain their original outcomes. New runs are needed for a comparison
under the revised contract; do not silently relabel the old results.

## Selective rerun

First check the dynamic deterministic recipes without models:

```bash
uv run browser-eval refresh \
  --manifest runs/linkedin-20260907/run-manifest.json \
  --task-path tasks/experimental/marca-real-madrid-open-en.yaml \
              tasks/experimental/amazon-cheapest-coffee-beans-en.yaml \
  --references-only
```

Both recipes passed three live headless trials during implementation. They discover
current article/product links from the site, then apply the same verifier as the agents.

To rerun all four runners for these two tasks (24 trials with the recorded three
repetitions), run the same command without `--references-only`. Refresh inherits the
original model, budgets, runner set, rendering mode, headless setting and seeds.
It keeps the other 60 task artifacts. The replacements run in a unique subdirectory;
after a complete matrix exists, the parent manifest selects the replacement artifacts
and records the rerun. Failed trials remain failures and are included. Earlier files
and the previous manifest remain available locally for recovery.

Then regenerate the existing report:

```bash
uv run browser-eval report \
  --manifest runs/linkedin-20260907/run-manifest.json \
  --output docs/results/english-repeated-20260907.md
```

Review the README summary against the new report before publishing. Do not relabel
earlier runs as if they had executed these revised tasks.
