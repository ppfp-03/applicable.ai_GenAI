"""The eligibility package stays deterministic by construction.

It must not reach the demo rules, the UI, a model provider or the ranking
layer. These are checked statically, so a stray import fails the build even
if it is never executed.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PACKAGE_ROOT = (
    Path(__file__).resolve().parents[2] / "src" / "oi" / "intelligence" / "eligibility"
)

FORBIDDEN_PREFIXES = (
    "core",
    "ui",
    "views",
    "streamlit",
    "oi.providers",
    "oi.ui",
    "oi.intelligence.ranking",
    "oi.intelligence.extraction",
    "oi.intelligence.explanations",
    "oi.intelligence.clarification",
    "anthropic",
    "openai",
    "random",
    "time",
)


def _module_files() -> list[Path]:
    return sorted(PACKAGE_ROOT.rglob("*.py"))


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.append(node.module)
    return names


def test_package_exists_and_has_modules() -> None:
    assert (PACKAGE_ROOT / "__init__.py").is_file()
    assert _module_files()


def test_legacy_stub_module_is_gone() -> None:
    # A module and a package cannot share the name `eligibility`.
    assert not PACKAGE_ROOT.with_suffix(".py").exists()


@pytest.mark.parametrize(
    "path", _module_files(), ids=lambda p: str(p.relative_to(PACKAGE_ROOT))
)
def test_no_forbidden_imports(path: Path) -> None:
    for name in _imported_modules(path):
        for prefix in FORBIDDEN_PREFIXES:
            assert not (name == prefix or name.startswith(prefix + ".")), (
                f"{path.name} imports {name}"
            )
