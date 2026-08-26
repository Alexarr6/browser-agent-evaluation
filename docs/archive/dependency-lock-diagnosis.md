# Browser Evaluation Dependency Lock Diagnosis

## Status

Dependency resolution originally completed without installation, but the generated
Python lockfile was too large for the former 1,200 changed-line work-unit budget.
The owner approved a narrow size exception on 2026-08-24. The complete lock and
approved dependencies are now installed; this diagnosis preserves the rationale.

## Measured diff

```text
pyproject.toml: +10 / -0
uv.lock:        +4,508 / -140
```

## Cause

`browser-use==0.13.8` brings a broad optional browser/LLM/document-processing
ecosystem. `uv` records cross-platform and multi-Python resolution metadata,
including packages not selected on this ARM64 runtime. The lock also keeps the
existing incompatible `review-lab` and `browser-eval` groups explicitly
conflicted, with separate valid `rich` resolutions.

## Safety outcome

- Python dependencies were installed only through `uv sync --frozen --group
  browser-eval`.
- Node dependencies were installed only through `npm ci --ignore-scripts`.
- Chromium ARM64, its matching headless shell and FFmpeg were downloaded by
  Playwright, but Chromium was not launched.
- No MCP process, model request or browser/public-site runtime occurred.

## Resolution

The complete generated `uv.lock` is retained under the owner's narrowly scoped
size exception. It must not be replaced with a host-specific or hand-edited lock,
because that would weaken reproducibility and verification.
