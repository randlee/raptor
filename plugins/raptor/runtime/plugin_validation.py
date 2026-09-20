from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from .vendor import check

COMMANDS = {
    "raptor:import": "./skills/import/SKILL.md",
    "raptor:export": "./skills/export/SKILL.md",
    "raptor:validate": "./skills/validate/SKILL.md",
    "raptor:round-trip": "./skills/round-trip/SKILL.md",
}
AGENTS = {
    "markdown-json-import",
    "json-sqlite-import",
    "sqlite-json-export",
    "markdown-validate",
    "json-validate",
    "sqlite-validate",
    "json-markdown-export",
    "migration-round-trip",
}
SKILLS = {"import", "export", "validate", "round-trip"}
REQUIRED_AGENT_SECTIONS = {
    "## Purpose",
    "## Inputs",
    "## Execution Steps",
    "## Output Format",
    "## Error Handling",
    "## Constraints",
}


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


def validate_plugin(plugin_root: Path, guideline: Path) -> None:
    root = plugin_root.resolve()
    guideline_text = guideline.resolve().read_text(encoding="utf-8")
    if "Document version: 0.7" not in guideline_text:
        raise PluginValidationError("pinned guideline is not v0.7")
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
    registry = json.loads((root / "agents/registry.yaml").read_text())
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
        for reference in re.findall(r"`(references/[^`]+\.md)`", text):
            if not (path.parent / reference).is_file():
                raise PluginValidationError(
                    f"broken skill reference: {name}/{reference}"
                )
        if (
            "Do not invoke an agent" not in text
            and "without invoking an agent" not in text
        ):
            raise PluginValidationError(f"A3 skill can delegate unexpectedly: {name}")
    inventory = manifest.get("inventory")
    if not isinstance(inventory, list) or len(inventory) != len(set(inventory)):
        raise PluginValidationError("plugin inventory is invalid")
    for relative in inventory:
        if not isinstance(relative, str) or not (root / relative).is_file():
            raise PluginValidationError(f"missing packaged file: {relative}")
    check(root)


__all__ = ["PluginValidationError", "validate_plugin"]
