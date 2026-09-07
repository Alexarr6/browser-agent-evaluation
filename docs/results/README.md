# Current result report

The current English evaluation uses one canonical seven-task matrix: five standard tasks
and two experimental tasks. Both categories are required in every complete run. The
experimental label discloses weaker acceptance coverage; it does not make those tasks
optional or exclude them from aggregate reporting.

The published result is the
[7 September 2026 repeated evaluation](english-repeated-20260907.md). It contains the
complete seven-task matrix, three repetitions, aggregate observations, interpretation
warnings and a hash inventory for all 84 sanitized evidence artifacts.

Generate future reports from the `run-manifest.json` written by a completed
`browser-eval repeat` execution. The manifest is the source of truth for task membership,
repetitions, model, limits, seeds, browser mode, browser versions and evidence files.

```bash
uv run browser-eval report \
  --manifest runs/<run-name>/run-manifest.json \
  --output docs/results/english-repeated-YYYYMMDD.md
```

Older pilot and diagnostic reports have been removed so visitors see only the result
produced by the current seven-task evaluation flow. Provider selection for future runs
lives in `experiment.yaml` and local credential environment variables.
