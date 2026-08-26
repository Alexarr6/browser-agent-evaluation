# Package architecture

The package is organized by responsibility rather than framework file type. Dependency
flow points inward toward `core`; orchestration and CLI code depend on runtime adapters,
not the reverse.

```text
cli -> evaluation -> agents/connectors -> browser/providers
                 \-> workflows/reporting
all application layers -> core
configuration is read by outer layers; core does not read configuration
```

## Modules

| Package | Responsibility |
|---|---|
| `core` | Stable task, action, evidence, policy, budget, assertion, and pricing contracts. |
| `configuration` | Strict configuration models, environment-aware loading, paths, and preflight. |
| `browser` | Playwright execution, isolated contexts, binaries, and runtime environment. |
| `providers` | Provider protocol and OpenAI-compatible model client behavior. |
| `agents` | Agent-specific planning and execution for restricted, browser-use, MCP, and reference. |
| `adapters` | Framework capability and launch contracts used during preflight. |
| `connectors` | Persistent workflow-session implementations behind the common connector boundary. |
| `workflows` | Workflow contracts, orchestration, and step receipts. |
| `evaluation` | One-shot trials, task recipes, randomized rounds, and smoke orchestration. |
| `reporting` | Sanitized evidence writing and aggregate report rendering. |
| `cli` | Argument parsing and command dispatch only. |

## Boundary rules

- `core` cannot import browser frameworks, providers, connectors, or CLI modules.
- CLI modules parse input and delegate; they do not implement browser behavior.
- Agent-specific tool normalization stays with that agent.
- Browser isolation and Playwright primitives stay under `browser`.
- Persistent sessions implement `connectors.base`; evaluation rounds do not depend on
  connector implementation details.
- Generated evidence goes to ignored runtime directories. Only selected sanitized
  reports belong under `docs/results`.
- New generic `utils` or `helpers` modules are prohibited. Place behavior with the
  domain or runtime responsibility that owns it.

## Public command

Use the installed command rather than importing internal modules:

```bash
uv run browser-eval repeat --help
```

Internal modules are not a compatibility API. Tests may import concrete contracts from
the package that owns them.
