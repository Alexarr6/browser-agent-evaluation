from __future__ import annotations

from collections.abc import Sequence

from browser_agent_evaluation.evaluation.smoke import main as run_smoke


def main(argv: Sequence[str] | None = None) -> None:
    if argv:
        raise SystemExit("browser-eval smoke does not accept command-line arguments")
    run_smoke()
