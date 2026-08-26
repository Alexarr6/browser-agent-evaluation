from __future__ import annotations

from dataclasses import dataclass

from browser_agent_evaluation.runners.base import (
    AdapterCapabilities,
    AdapterConfiguration,
    validate_adapter_configuration,
)


@dataclass(frozen=True)
class BrowserUseAdapter:
    """Compatibility gate; runtime binding is intentionally optional and lazy."""

    capabilities: AdapterCapabilities

    def preflight(self, configuration: AdapterConfiguration) -> None:
        if configuration.runner != "browser_use":
            raise ValueError("browser-use adapter requires browser_use runner configuration")
        validate_adapter_configuration(configuration, self.capabilities)
