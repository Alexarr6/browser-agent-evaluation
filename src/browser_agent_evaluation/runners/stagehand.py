from __future__ import annotations

import json
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from browser_agent_evaluation.runners.base import (
    AdapterCapabilities,
    AdapterConfiguration,
    validate_adapter_configuration,
)


class NdjsonBridgeError(RuntimeError):
    """Raised when a Stagehand bridge message violates the bounded wire contract."""


class StagehandRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=1, max_length=128)
    procedure: str = Field(min_length=1, max_length=8_000)
    completion_text: str = Field(min_length=1, max_length=4_000)
    allowed_domains: list[str] = Field(min_length=1, max_length=16)
    action_limit: int = Field(ge=1, le=100)
    timeout_seconds: int = Field(ge=1, le=300)


def encode_request(request: StagehandRequest, *, max_bytes: int = 16_384) -> bytes:
    line = (json.dumps(request.model_dump(mode="json"), separators=(",", ":")) + "\n").encode()
    if len(line) > max_bytes:
        raise NdjsonBridgeError("Stagehand request exceeds bridge maximum")
    return line


@dataclass(frozen=True)
class StagehandAdapter:
    """Preflight-only Stagehand bridge; Node execution is approval-gated later."""

    capabilities: AdapterCapabilities

    def preflight(self, configuration: AdapterConfiguration) -> None:
        if configuration.runner != "stagehand":
            raise ValueError("Stagehand adapter requires stagehand runner configuration")
        validate_adapter_configuration(configuration, self.capabilities)
