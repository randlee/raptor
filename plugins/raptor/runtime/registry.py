from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Any, cast

from .strict_json import loads

AGENTS = {
    "json-markdown-export",
    "json-sqlite-import",
    "json-validate",
    "markdown-json-import",
    "markdown-validate",
    "migration-round-trip",
    "sqlite-json-export",
    "sqlite-validate",
}
SKILLS = {"export", "import", "round-trip", "validate"}
_VERSION = re.compile(r"[1-9][0-9]*\.[0-9]+\.[0-9]+")
_CONSTRAINT = re.compile(r"[1-9][0-9]*\.(?:x|[0-9]+\.[0-9]+)")
_HASH = re.compile(r"[0-9a-f]{64}")


def parse_registry(text: str) -> dict[str, Any]:
    value = loads(text)
    if not isinstance(value, dict) or set(value) != {"agents", "skills"}:
        raise ValueError("invalid registry root")
    agents, skills = value["agents"], value["skills"]
    if not isinstance(agents, dict) or set(agents) != AGENTS:
        raise ValueError("invalid registry agents")
    if not isinstance(skills, dict) or set(skills) != SKILLS:
        raise ValueError("invalid registry skills")
    for name, entry in agents.items():
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256", "version"}:
            raise ValueError("invalid agent entry")
        path, digest, version = entry["path"], entry["sha256"], entry["version"]
        expected = PurePosixPath("agents") / f"{name}.md"
        if type(path) is not str or PurePosixPath(path) != expected:
            raise ValueError("invalid agent path")
        if type(digest) is not str or _HASH.fullmatch(digest) is None:
            raise ValueError("invalid agent hash")
        if type(version) is not str or _VERSION.fullmatch(version) is None:
            raise ValueError("invalid agent version")
    for entry in skills.values():
        if not isinstance(entry, dict) or set(entry) != {"depends_on"}:
            raise ValueError("invalid skill entry")
        dependencies = entry["depends_on"]
        if (
            not isinstance(dependencies, dict)
            or not dependencies
            or not set(dependencies) <= AGENTS
        ):
            raise ValueError("invalid skill dependencies")
        if any(
            type(item) is not str or _CONSTRAINT.fullmatch(item) is None
            for item in dependencies.values()
        ):
            raise ValueError("invalid dependency constraint")
    return cast(dict[str, Any], value)


__all__ = ["AGENTS", "SKILLS", "parse_registry"]
