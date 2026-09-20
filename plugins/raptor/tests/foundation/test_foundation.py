from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from runtime.plugin_validation import COMMANDS, validate_plugin
from runtime import routes
from runtime.routes import route

ROOT = Path(__file__).parents[2]
REPO = ROOT.parents[1]


def test_dual_manifests_expose_exact_commands() -> None:
    for relative in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json"):
        assert json.loads((ROOT / relative).read_text())["skills"] == "./skills/"
    discovered = {
        f"raptor:{path.parent.name}": f"./skills/{path.parent.name}/SKILL.md"
        for path in ROOT.glob("skills/*/SKILL.md")
    }
    assert discovered == COMMANDS


def test_all_a3_routes_are_structured_unsupported() -> None:
    for command in ("import", "export", "validate", "round-trip"):
        result = route(command, "json", "sqlite")
        assert result["success"] is False
        assert result["error"]["code"] == "RAPTOR.UNSUPPORTED.PHASE"
    assert route("import", "json", "dolt")["error"]["code"] == "RAPTOR.UNSUPPORTED.DOLT"


def test_dependency_failure_stops_before_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failure = {"success": False, "error": {"code": "RAPTOR.DEPENDENCY.INCOMPATIBLE"}}
    monkeypatch.setattr(routes, "dependency_error", lambda: failure)
    assert route("import", "markdown", "json") is failure


def test_plugin_validator() -> None:
    validate_plugin(
        ROOT,
        REPO
        / "docs/plans/phase-a/references/claude-code-skills-agents-guidelines-v0.7.md",
    )


def test_scripts_are_thin_runtime_wrappers() -> None:
    forbidden = {"sqlite3", "subprocess", "shutil", "hashlib"}
    for path in (ROOT / "scripts").glob("*.py"):
        tree = ast.parse(path.read_text())
        imports = {
            node.names[0].name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom)) and node.names
        }
        assert not imports & forbidden
        assert len(list(ast.walk(tree))) < 260
