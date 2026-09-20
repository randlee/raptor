from __future__ import annotations

import ast
import json
import shutil
from pathlib import Path

import pytest

from runtime.plugin_validation import COMMANDS, validate_plugin
from runtime.plugin_validation import PluginValidationError
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


def test_all_twelve_a3_routes_are_structured_unsupported_without_invocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import runtime.agent_runner as runner

    invoked = False

    def forbidden(**values: object) -> object:
        nonlocal invoked
        invoked = True
        raise AssertionError(values)

    monkeypatch.setattr(runner, "run_agent", forbidden)
    cases = [
        ("import", "markdown", "json"),
        ("import", "json", "sqlite"),
        ("import", "json", "dolt"),
        ("export", "sqlite", "json"),
        ("export", "json", "markdown"),
        ("export", "dolt", "json"),
        ("validate", "markdown", None),
        ("validate", "json", None),
        ("validate", "sqlite", None),
        ("validate", "dolt", None),
        ("round-trip", "migration", None),
        ("round-trip", "dolt", None),
    ]
    for command, source, target in cases:
        result = route(command, source, target)
        assert result["success"] is False
        expected = (
            "RAPTOR.UNSUPPORTED.DOLT"
            if "dolt" in {source, target}
            else "RAPTOR.UNSUPPORTED.PHASE"
        )
        assert result["error"]["code"] == expected
    assert not invoked


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


def test_ci_wires_complete_case_insensitive_exclusion_gates() -> None:
    workflow = (REPO / ".github/workflows/ci.yml").read_text().lower()
    for value in (
        "test ! -e schema/sql/dolt",
        "test ! -e plugins/raptor/templates",
        "-iname 'marketplace.json'",
        "-iname 'templates'",
        "grep -ei '/(import|export|render|round[-_]?trip|transform|convert).*\\.py$'",
        "rg -ni",
        "p3" + "-documentation",
        "req" + "-p3-",
        "nfr" + "-p3-",
        "adr" + "-p3-",
        "\\b" + "n" + "ft\\b",
        "sql" + "x",
        "sc" + "-compose",
        "__pycache__",
        "*.pyc",
    ):
        assert value in workflow


@pytest.mark.parametrize(
    "relative",
    ["Marketplace.JSON", "Templates/example.j2", "scripts/ReNdEr-artifact.py"],
)
def test_validator_rejects_marketplace_template_and_transformation_paths(
    tmp_path: Path, relative: str
) -> None:
    plugin = tmp_path / "raptor"
    shutil.copytree(
        ROOT, plugin, ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyc")
    )
    path = plugin / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("forbidden")
    with pytest.raises(
        PluginValidationError, match="marketplace, template, or transformation"
    ):
        validate_plugin(
            plugin,
            REPO
            / "docs/plans/phase-a/references/claude-code-skills-agents-guidelines-v0.7.md",
        )
