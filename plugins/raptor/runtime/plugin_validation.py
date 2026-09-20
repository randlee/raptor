from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path
from typing import cast
from .vendor import check
from .routes import unsupported_envelope
from .strict_json import loads
from .registry import AGENTS, SKILLS, parse_registry

COMMANDS = {
    "raptor:import": "./skills/import/SKILL.md",
    "raptor:export": "./skills/export/SKILL.md",
    "raptor:validate": "./skills/validate/SKILL.md",
    "raptor:round-trip": "./skills/round-trip/SKILL.md",
}
REQUIRED_AGENT_SECTIONS = {
    "## Purpose",
    "## Inputs",
    "## Execution Steps",
    "## Output Format",
    "## Error Handling",
    "## Constraints",
}
SCRIPT_CONTRACTS: dict[str, dict[str, object]] = {
    "run_agent.py": {
        "imports": frozenset(
            {
                "__future__.annotations",
                "argparse",
                "json",
                "pathlib.Path",
                "runtime.agent_runner.run_agent",
                "runtime.cli.emit",
                "runtime.cli.failure",
                "runtime.client_adapters.claude.ClaudeBackend",
                "runtime.client_adapters.codex.CodexBackend",
                "sys",
            }
        ),
        "functions": frozenset({"main"}),
        "calls": frozenset(
            {
                "Call.resolve",
                "ClaudeBackend",
                "CodexBackend",
                "Path",
                "SystemExit",
                "argparse.ArgumentParser",
                "emit",
                "failure",
                "json.loads",
                "main",
                "parser.add_argument",
                "parser.parse_args",
                "run_agent",
                "str",
                "sys.path.insert",
            }
        ),
        "assignments": (
            "arguments",
            "backend",
            "parser",
            "result",
            "result",
            "sys.dont_write_bytecode",
        ),
        "lambdas": 0,
        "top": (
            "ImportFrom",
            "Import",
            "Import",
            "Import",
            "ImportFrom",
            "Assign",
            "Expr",
            "ImportFrom",
            "ImportFrom",
            "ImportFrom",
            "ImportFrom",
            "FunctionDef",
            "If",
        ),
    },
    "validate_plugin.py": {
        "imports": frozenset(
            {
                "__future__.annotations",
                "argparse",
                "pathlib.Path",
                "runtime.cli.invoke",
                "runtime.plugin_validation.validate_plugin",
                "sys",
            }
        ),
        "functions": frozenset({"main"}),
        "calls": frozenset(
            {
                "Call.resolve",
                "Path",
                "SystemExit",
                "argparse.ArgumentParser",
                "invoke",
                "main",
                "parser.add_argument",
                "parser.parse_args",
                "str",
                "sys.path.insert",
                "validate_plugin",
            }
        ),
        "assignments": ("arguments", "parser", "sys.dont_write_bytecode"),
        "lambdas": 1,
        "top": (
            "ImportFrom",
            "Import",
            "Import",
            "ImportFrom",
            "Assign",
            "Expr",
            "ImportFrom",
            "ImportFrom",
            "FunctionDef",
            "If",
        ),
    },
    "vendor_schema.py": {
        "imports": frozenset(
            {
                "__future__.annotations",
                "argparse",
                "pathlib.Path",
                "runtime.cli.invoke",
                "runtime.vendor.check",
                "runtime.vendor.refresh",
                "sys",
                "typing.Any",
            }
        ),
        "functions": frozenset({"_run", "main"}),
        "calls": frozenset(
            {
                "Call.resolve",
                "Path",
                "SystemExit",
                "_run",
                "argparse.ArgumentParser",
                "check",
                "invoke",
                "main",
                "parser.add_argument",
                "parser.parse_args",
                "refresh",
                "str",
                "sys.path.insert",
            }
        ),
        "assignments": (
            "arguments",
            "parser",
            "root",
            "sys.dont_write_bytecode",
        ),
        "lambdas": 1,
        "top": (
            "ImportFrom",
            "Import",
            "Import",
            "ImportFrom",
            "ImportFrom",
            "Assign",
            "Expr",
            "ImportFrom",
            "ImportFrom",
            "FunctionDef",
            "FunctionDef",
            "If",
        ),
    },
}

_OPERATION_TOP = (
    "ImportFrom",
    "Import",
    "Import",
    "ImportFrom",
    "Assign",
    "Assign",
    "Expr",
    "ImportFrom",
    "Expr",
    "ImportFrom",
    "ImportFrom",
    "FunctionDef",
    "If",
)
_OPERATION_IMPORTS = {
    "__future__.annotations",
    "argparse",
    "pathlib.Path",
    "runtime.bootstrap.bootstrap",
    "runtime.cli.invoke",
    "sys",
}
_OPERATION_CALLS = {
    "Call.resolve",
    "Path",
    "SystemExit",
    "argparse.ArgumentParser",
    "bootstrap",
    "invoke",
    "main",
    "parser.add_argument",
    "parser.parse_args",
    "str",
    "sys.path.insert",
}


def _operation_contract(
    runtime_imports: set[str],
    operation_calls: set[str],
    *,
    functions: set[str] | None = None,
    assignments: tuple[str, ...] | None = None,
    calls: set[str] | None = None,
    lambdas: int = 1,
    top: tuple[str, ...] = _OPERATION_TOP,
) -> dict[str, object]:
    return {
        "imports": frozenset(_OPERATION_IMPORTS | runtime_imports),
        "functions": frozenset(functions or {"main"}),
        "calls": frozenset(_OPERATION_CALLS | operation_calls | (calls or set())),
        "assignments": assignments
        or ("PLUGIN_ROOT", "arguments", "mode", "parser", "sys.dont_write_bytecode"),
        "lambdas": lambdas,
        "top": top,
    }


SCRIPT_CONTRACTS.update(
    {
        "markdown_to_json.py": _operation_contract(
            {"runtime.operations.markdown_to_json"},
            {"markdown_to_json"},
            calls={"mode.add_argument", "parser.add_mutually_exclusive_group"},
        ),
        "import_sqlite.py": _operation_contract(
            {"runtime.operations.import_sqlite"},
            {"import_sqlite"},
            calls={"mode.add_argument", "parser.add_mutually_exclusive_group"},
        ),
        "export_sqlite.py": _operation_contract(
            {"runtime.operations.export_sqlite"},
            {"export_sqlite"},
            calls={"mode.add_argument", "parser.add_mutually_exclusive_group"},
        ),
        "identity.py": _operation_contract(
            {"runtime.identity.register_identity"},
            {"register_identity"},
            assignments=(
                "PLUGIN_ROOT",
                "arguments",
                "mode",
                "parser",
                "register",
                "subparsers",
                "sys.dont_write_bytecode",
            ),
            calls={
                "mode.add_argument",
                "parser.add_subparsers",
                "register.add_argument",
                "register.add_mutually_exclusive_group",
                "subparsers.add_parser",
            },
        ),
        "validate.py": _operation_contract(
            {
                "runtime.operations.validate_json",
                "runtime.operations.validate_markdown",
                "runtime.operations.validate_sqlite",
            },
            {"validate_json", "validate_markdown", "validate_sqlite"},
            functions={"main", "_required"},
            assignments=(
                "PLUGIN_ROOT",
                "arguments",
                "parser",
                "sys.dont_write_bytecode",
            ),
            calls={"ValueError", "_required"},
            lambdas=3,
            top=_OPERATION_TOP[:-2] + ("FunctionDef", "FunctionDef", "If"),
        ),
    }
)
SCRIPT_CONTRACTS["identity.py"]["calls"] = frozenset(
    cast(frozenset[str], SCRIPT_CONTRACTS["identity.py"]["calls"])
    - {"parser.add_argument"}
)


class PluginValidationError(ValueError):
    pass


def _frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise PluginValidationError(f"missing YAML frontmatter: {path}")
    block = text.split("---\n", 2)[1]
    values: dict[str, str] = {}
    parent = ""
    for line in block.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            if line.startswith("  ") and parent:
                values[f"{parent}.{key.strip()}"] = value.strip()
            else:
                parent = key.strip() if not value.strip() else ""
                values[key.strip()] = value.strip()
    return values


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _node_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_node_name(node.value)}.{node.attr}"
    return type(node).__name__


def _validate_scripts(root: Path) -> None:
    scripts = {path.name: path for path in (root / "scripts").glob("*.py")}
    if set(scripts) != set(SCRIPT_CONTRACTS):
        raise PluginValidationError("scripts are not the exact thin-wrapper inventory")
    for name, path in scripts.items():
        contract = SCRIPT_CONTRACTS[name]
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = {
            (
                item.name
                if isinstance(node, ast.Import)
                else f"{node.module}.{item.name}"
            )
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for item in node.names
        }
        assignments: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                assignments.extend(_node_name(item) for item in node.targets)
            elif isinstance(node, ast.AnnAssign):
                assignments.append(_node_name(node.target))
        if (
            imports != contract["imports"]
            or {
                node.name
                for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef)
            }
            != contract["functions"]
            or {
                _node_name(node.func)
                for node in ast.walk(tree)
                if isinstance(node, ast.Call)
            }
            != contract["calls"]
            or tuple(sorted(assignments)) != contract["assignments"]
            or sum(isinstance(node, ast.Lambda) for node in ast.walk(tree))
            != contract["lambdas"]
            or tuple(type(node).__name__ for node in tree.body) != contract["top"]
        ):
            raise PluginValidationError("scripts must remain thin runtime wrappers")


def validate_plugin(plugin_root: Path, guideline: Path) -> None:
    root = plugin_root.resolve()
    guideline_text = guideline.resolve().read_text(encoding="utf-8")
    if "Document version: 0.7" not in guideline_text:
        raise PluginValidationError("pinned guideline is not v0.7")
    _validate_scripts(root)
    manifests = [
        json.loads((root / ".claude-plugin/plugin.json").read_text()),
        json.loads((root / ".codex-plugin/plugin.json").read_text()),
    ]
    if any(
        item.get("name") != "raptor" or item.get("skills") != "./skills/"
        for item in manifests
    ):
        raise PluginValidationError(
            "client manifests do not expose the shared skill root"
        )
    discovered = {
        f"raptor:{path.parent.name}": f"./skills/{path.parent.name}/SKILL.md"
        for path in root.glob("skills/*/SKILL.md")
    }
    if discovered != COMMANDS:
        raise PluginValidationError(
            "clients do not discover exactly four public commands"
        )
    registry = parse_registry((root / "agents/registry.yaml").read_text())
    if (
        set(registry.get("agents", {})) != AGENTS
        or set(registry.get("skills", {})) != SKILLS
    ):
        raise PluginValidationError(
            "registry inventory differs from the authoritative set"
        )
    for skill, skill_entry in registry["skills"].items():
        dependencies = skill_entry.get("depends_on")
        if not isinstance(dependencies, dict) or not dependencies:
            raise PluginValidationError(f"skill has no registry dependencies: {skill}")
        for agent, constraint in dependencies.items():
            entry = registry["agents"].get(agent)
            if entry is None:
                raise PluginValidationError(
                    f"skill depends on unknown agent: {skill}/{agent}"
                )
            version = entry["version"]
            compatible_major = (
                isinstance(constraint, str)
                and constraint.endswith(".x")
                and version.split(".", 1)[0] == constraint[:-2]
            )
            if constraint != version and not compatible_major:
                raise PluginValidationError(
                    f"skill version constraint is incompatible: {skill}/{agent}"
                )
    manifest = json.loads((root / "plugin-manifest.json").read_text())
    for name, entry in registry["agents"].items():
        path = (root / entry["path"]).resolve()
        if path.parent != (root / "agents").resolve() or not path.is_file():
            raise PluginValidationError(f"invalid registered path: {name}")
        frontmatter = _frontmatter(path)
        if (
            frontmatter.get("name") != name
            or frontmatter.get("version") != entry["version"]
        ):
            raise PluginValidationError(f"agent frontmatter mismatch: {name}")
        body = path.read_text(encoding="utf-8")
        if not REQUIRED_AGENT_SECTIONS.issubset(body.splitlines()):
            raise PluginValidationError(f"agent contract is incomplete: {name}")
        if "exactly one fenced JSON standard envelope" not in body:
            raise PluginValidationError(
                f"agent response contract is incomplete: {name}"
            )
        digest = _sha(path)
        if digest != entry.get("sha256") or digest != manifest.get("agents", {}).get(
            name
        ):
            raise PluginValidationError(f"agent hash mismatch: {name}")
    for name in SKILLS:
        path = root / f"skills/{name}/SKILL.md"
        frontmatter = _frontmatter(path)
        if frontmatter.get("name") != name or not re.fullmatch(
            r"\d+\.\d+\.\d+", frontmatter.get("metadata.version", "")
        ):
            raise PluginValidationError(f"skill frontmatter mismatch: {name}")
        text = path.read_text(encoding="utf-8")
        if "`../runtime-preflight.md`" not in text:
            raise PluginValidationError(f"skill omits shared runtime preflight: {name}")
        for reference in re.findall(r"`(references/[^`]+\.md)`", text):
            if not (path.parent / reference).is_file():
                raise PluginValidationError(
                    f"broken skill reference: {name}/{reference}"
                )
        if name in {"import", "export", "validate"}:
            if "Agent Runner" not in text:
                raise PluginValidationError(
                    f"active skill omits the shared runner: {name}"
                )
        elif (
            "Do not invoke an agent" not in text
            and "without invoking an agent" not in text
        ):
            raise PluginValidationError(
                f"unsupported skill can delegate unexpectedly: {name}"
            )
    preflight = (root / "skills/runtime-preflight.md").read_text(encoding="utf-8")
    for location in (
        "$HOME/.local/bin/python3",
        "$HOME/.venvs/python3/bin/python3",
        "$(python3 -m site --user-base 2>/dev/null)/bin/python3",
        "/opt/homebrew/bin/python3",
    ):
        if location not in preflight:
            raise PluginValidationError(
                f"runtime preflight omits common location: {location}"
            )
    route_references = [
        path
        for path in root.glob("skills/*/references/*.md")
        if path.name != "installation-and-troubleshooting.md"
    ]
    unsupported_names = {
        "json-dolt.md",
        "json-markdown.md",
        "dolt-json.md",
        "dolt.md",
        "migration.md",
    }
    unsupported_references = [
        path for path in route_references if path.name in unsupported_names
    ]
    if (
        len(route_references) != 12
        or len(unsupported_references) != 6
        or any(
            "../../unsupported-responses.md" not in path.read_text(encoding="utf-8")
            for path in unsupported_references
        )
    ):
        raise PluginValidationError(
            "route references do not share the deterministic unsupported contract"
        )
    policy_text = (root / "skills/unsupported-responses.md").read_text(encoding="utf-8")
    sections = re.findall(
        r"## (Sprint A4|Sprint A5|Dolt)\n\n```json\n([^\n]+)\n```", policy_text
    )
    if len(sections) != 3 or any(
        loads(body) != unsupported_envelope(name) for name, body in sections
    ):
        raise PluginValidationError(
            "unsupported response documentation drifted from runtime policy"
        )
    inventory = manifest.get("inventory")
    if not isinstance(inventory, list) or len(inventory) != len(set(inventory)):
        raise PluginValidationError("plugin inventory is invalid")
    for relative in inventory:
        if not isinstance(relative, str) or not (root / relative).is_file():
            raise PluginValidationError(f"missing packaged file: {relative}")
    if any(
        path.name == "__pycache__" or path.suffix.casefold() in {".pyc", ".pyo"}
        for path in root.rglob("*")
    ):
        raise PluginValidationError("plugin inventory contains bytecode artifacts")
    forbidden_paths = [
        path
        for path in root.rglob("*")
        if path.name.casefold() in {"marketplace.json", "templates"}
        or (
            path.parent == root / "scripts"
            and path.name
            not in {"markdown_to_json.py", "import_sqlite.py", "export_sqlite.py"}
            and re.search(
                r"(?:import|export|render|round[-_]?trip|transform|convert)",
                path.stem,
                re.I,
            )
        )
    ]
    if forbidden_paths:
        raise PluginValidationError(
            "plugin contains marketplace, template, or transformation paths"
        )
    check(root)


__all__ = ["PluginValidationError", "validate_plugin"]
