from __future__ import annotations

from pathlib import Path

REFERENCE_CHROMIUM = Path.home() / ".cache/ms-playwright/chromium-1234/chrome-linux/chrome"
BROWSER_USE_CHROMIUM = Path.home() / ".cache/ms-playwright/chromium-1187/chrome-linux/chrome"

MCP_ACTION_TIMEOUT_SECONDS = 60
MCP_NAVIGATION_TIMEOUT_SECONDS = 90
