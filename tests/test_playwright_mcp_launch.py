from __future__ import annotations

from pathlib import Path

from browser_agent_evaluation.runners.playwright_mcp import (
    McpLaunchConfiguration,
    build_mcp_command,
)


def test_mcp_command_requires_shared_headless_isolated_browser() -> None:
    command = build_mcp_command(
        node_path=Path("/usr/bin/node"),
        cli_path=Path("/opt/playwright-mcp/cli.js"),
        configuration=McpLaunchConfiguration(
            chromium_executable=Path("/opt/chromium/chrome"),
            output_directory=Path("/tmp/mcp-output"),
            allowed_origins=["https://www.wikipedia.org", "https://en.wikipedia.org"],
            timeout_seconds=60,
        ),
    )

    assert command == [
        "/usr/bin/node",
        "/opt/playwright-mcp/cli.js",
        "--headless",
        "--isolated",
        "--block-service-workers",
        "--executable-path",
        "/opt/chromium/chrome",
        "--output-dir",
        "/tmp/mcp-output",
        "--allowed-origins",
        "https://www.wikipedia.org;https://en.wikipedia.org",
        "--timeout-action",
        "60000",
        "--timeout-navigation",
        "60000",
    ]


def test_mcp_launch_configuration_rejects_no_allowed_origin() -> None:
    try:
        McpLaunchConfiguration(
            chromium_executable=Path("/opt/chromium/chrome"),
            output_directory=Path("/tmp/mcp-output"),
            allowed_origins=[],
            timeout_seconds=60,
        )
    except ValueError as error:
        assert "allowed origins" in str(error)
    else:
        raise AssertionError("empty origin policy must fail")
