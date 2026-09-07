from __future__ import annotations

import sys
from collections.abc import Callable, Sequence

from browser_agent_evaluation.cli import micro, repeat, report, smoke

_COMMANDS: dict[str, Callable[[Sequence[str] | None], None]] = {
    "micro": micro.main,
    "repeat": repeat.main,
    "report": report.main,
    "smoke": smoke.main,
}


def main(argv: Sequence[str] | None = None) -> None:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments or arguments[0] in {"-h", "--help"}:
        print("Usage: browser-eval {repeat|report|smoke|micro} [options]")
        return
    command = arguments.pop(0)
    handler = _COMMANDS.get(command)
    if handler is None:
        raise SystemExit(f"unknown command: {command}")
    handler(arguments)
