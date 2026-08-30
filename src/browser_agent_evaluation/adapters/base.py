from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict

from browser_agent_evaluation.core.models import RunnerName, TaskSpec, TrialEvidence


class AdapterContractError(RuntimeError):
    """Raised when a runner cannot produce comparable, safe trial evidence."""


class AdapterConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    runner: RunnerName
    provider: str
    model: str
    endpoint: str
    headless: bool
    fresh_profile: bool
    cleanup_evidence_required: bool


@dataclass(frozen=True)
class AdapterCapabilities:
    supports_common_model: bool
    reports_usage: bool
    reports_cleanup: bool
    observation_mode: Literal["accessibility_dom", "framework_owned", "mcp_accessibility"]


class BrowserRunner(Protocol):
    async def run(self, task: TaskSpec, configuration: AdapterConfiguration) -> TrialEvidence: ...


def validate_adapter_configuration(
    configuration: AdapterConfiguration, capabilities: AdapterCapabilities
) -> None:
    if not configuration.provider.strip() or not configuration.model.strip():
        raise AdapterContractError("adapter must identify its configured provider and model")
    if not configuration.endpoint.startswith("https://"):
        raise AdapterContractError("adapter provider endpoint must use HTTPS")
    if not configuration.headless:
        raise AdapterContractError("adapter must use headless browser mode")
    if not configuration.fresh_profile:
        raise AdapterContractError("adapter must use a fresh browser profile")
    if configuration.cleanup_evidence_required and not capabilities.reports_cleanup:
        raise AdapterContractError("adapter must report cleanup evidence")
    if not capabilities.supports_common_model:
        raise AdapterContractError("adapter cannot use the common model")
    if not capabilities.reports_usage:
        raise AdapterContractError("adapter cannot report comparable usage")
