from __future__ import annotations

from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PACKAGE_ROOT.parent
PROJECT_ROOT = SOURCE_ROOT.parent
TASKS_ROOT = PROJECT_ROOT / "tasks"
NODE_MODULES_ROOT = PROJECT_ROOT / "node_modules"
