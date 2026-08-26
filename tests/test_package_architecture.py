from __future__ import annotations

import ast
from pathlib import Path

PACKAGE_ROOT = Path(__file__).parents[1] / "src/browser_agent_evaluation"


def _package_imports(path: Path) -> set[str]:
    imports: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
    return {name for name in imports if name.startswith("browser_agent_evaluation")}


def test_package_root_contains_only_public_entrypoints() -> None:
    assert {path.name for path in PACKAGE_ROOT.glob("*.py")} == {"__init__.py", "__main__.py"}


def test_core_has_no_outward_application_dependencies() -> None:
    for path in (PACKAGE_ROOT / "core").glob("*.py"):
        assert all(
            dependency == "browser_agent_evaluation.core"
            or dependency.startswith("browser_agent_evaluation.core.")
            for dependency in _package_imports(path)
        ), path


def test_generic_catch_all_modules_are_not_introduced() -> None:
    forbidden = {"utils.py", "helpers.py", "common.py", "misc.py"}
    assert not {path.name for path in PACKAGE_ROOT.rglob("*.py")} & forbidden
