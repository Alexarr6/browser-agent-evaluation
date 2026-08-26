from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field

from browser_agent_evaluation.adapters.base import (
    AdapterCapabilities,
    AdapterConfiguration,
    validate_adapter_configuration,
)


class ToolScopeError(RuntimeError):
    """Raised when the generic MCP arm receives a non-browser capability."""


@dataclass(frozen=True)
class McpLaunchConfiguration:
    chromium_executable: Path
    output_directory: Path
    allowed_origins: list[str]
    timeout_seconds: int

    def __post_init__(self) -> None:
        if not self.allowed_origins:
            raise ValueError("MCP launch requires allowed origins")
        if self.timeout_seconds < 1 or self.timeout_seconds > 300:
            raise ValueError("MCP timeout must be between 1 and 300 seconds")
        if any(not _is_https_origin(origin) for origin in self.allowed_origins):
            raise ValueError("MCP allowed origins must be HTTPS URLs")


def _is_https_origin(origin: str) -> bool:
    parsed = urlparse(origin)
    return parsed.scheme == "https" and bool(parsed.netloc)


def build_mcp_command(
    *, node_path: Path, cli_path: Path, configuration: McpLaunchConfiguration
) -> list[str]:
    timeout_ms = str(configuration.timeout_seconds * 1_000)
    return [
        str(node_path),
        str(cli_path),
        "--headless",
        "--isolated",
        "--block-service-workers",
        "--executable-path",
        str(configuration.chromium_executable),
        "--output-dir",
        str(configuration.output_directory),
        "--allowed-origins",
        ";".join(configuration.allowed_origins),
        "--timeout-action",
        timeout_ms,
        "--timeout-navigation",
        timeout_ms,
    ]


class McpToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=128)
    arguments: dict[str, Any]


@dataclass
class McpToolLoop:
    """A bounded, injected tool loop; it does not create an MCP transport."""

    call: Callable[[McpToolCall], dict[str, Any]]
    max_calls: int

    def execute(self, calls: Iterable[McpToolCall]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for tool_call in calls:
            if not tool_call.name.startswith("playwright."):
                raise ToolScopeError("only Playwright MCP tools are allowed")
            if len(results) >= self.max_calls:
                raise ToolScopeError("MCP tool call limit reached")
            results.append(self.call(tool_call))
        return results


@dataclass(frozen=True)
class PlaywrightMcpAdapter:
    """Preflight-only MCP scope gate; no MCP process is started here."""

    capabilities: AdapterCapabilities

    def preflight(self, configuration: AdapterConfiguration, tools: list[str]) -> None:
        if configuration.runner != "playwright_mcp":
            raise ValueError("Playwright MCP adapter requires playwright_mcp runner configuration")
        validate_adapter_configuration(configuration, self.capabilities)
        if not tools or any(not tool.startswith("playwright.") for tool in tools):
            raise ToolScopeError("only Playwright MCP tools are allowed")
