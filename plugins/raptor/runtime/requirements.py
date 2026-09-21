from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .strict_json import loads


def sc_compose_requirement(manifest: dict[str, Any]) -> dict[str, Any]:
    values = manifest.get("requires", {}).get("cli")
    if (
        not isinstance(values, list)
        or len(values) != 1
        or not isinstance(values[0], dict)
    ):
        raise ValueError("RAPTOR.MANIFEST.CLI: one CLI requirement is required")
    value = values[0]
    if (
        set(value) != {"name", "version", "version_command"}
        or value.get("name") != "sc-compose"
        or not isinstance(value.get("version"), str)
        or re.fullmatch(r">=\d+\.\d+\.\d+,<\d+\.\d+\.\d+", value["version"]) is None
        or value.get("version_command") != ["sc-compose", "--version"]
    ):
        raise ValueError("RAPTOR.MANIFEST.CLI: invalid sc-compose requirement")
    return dict(value)


def load_sc_compose_requirement(plugin_root: Path) -> dict[str, Any]:
    try:
        manifest = loads((plugin_root / "plugin-manifest.json").read_text())
    except (OSError, ValueError) as error:
        raise ValueError("RAPTOR.MANIFEST.CLI: invalid plugin manifest") from error
    if not isinstance(manifest, dict):
        raise ValueError("RAPTOR.MANIFEST.CLI: invalid plugin manifest")
    return sc_compose_requirement(manifest)


__all__ = ["load_sc_compose_requirement", "sc_compose_requirement"]
