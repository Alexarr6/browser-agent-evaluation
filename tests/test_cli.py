from __future__ import annotations

import pytest

from browser_agent_evaluation.cli.main import main
from browser_agent_evaluation.cli.repeat import build_parser


def test_root_cli_prints_bounded_command_help(capsys: pytest.CaptureFixture[str]) -> None:
    main(["--help"])

    assert capsys.readouterr().out == "Usage: browser-eval {repeat|smoke|micro} [options]\n"


def test_repeat_cli_exposes_rendering_profile_without_running() -> None:
    args = build_parser().parse_args(["--rendering-profile", "visual-parity"])

    assert args.rendering_profile == "visual-parity"


def test_root_cli_rejects_unknown_commands() -> None:
    with pytest.raises(SystemExit, match="unknown command"):
        main(["unknown"])
