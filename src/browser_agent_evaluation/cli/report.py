from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from browser_agent_evaluation.reporting.repeated import write_repeated_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="browser-eval report",
        description="Render a report from a completed evaluation manifest",
    )
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    print(write_repeated_report(manifest_path=args.manifest, output_path=args.output))
