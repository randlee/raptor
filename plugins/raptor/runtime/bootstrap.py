from __future__ import annotations

import importlib
import hashlib
import re
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path, PurePosixPath
from types import ModuleType
from typing import Any, cast

from .registry import AGENTS, parse_registry
from .strict_json import loads
from .vendor import (
    PYDANTIC_CONSTRAINT,
    SCHEMA_VERSION,
    TREE_ALGORITHM,
    _plugin_inventory,
    tree_hash,
)


class BootstrapError(RuntimeError):
    pass


def _pydantic_compatible(actual: str) -> bool:
    major, minor, *_ = (int(part) for part in actual.split(".") if part.isdigit())
    return major == 2 and minor >= 10


def _manifest(text: str) -> dict[str, Any]:
    try:
        value = loads(text)
    except ValueError as error:
        raise BootstrapError("RAPTOR.BOOTSTRAP.MANIFEST: malformed JSON") from error
    required = {"name", "version", "requires", "vendor", "agents", "inventory"}
    if not isinstance(value, dict) or set(value) != required:
        raise BootstrapError("RAPTOR.BOOTSTRAP.MANIFEST: invalid manifest root")
    requires, vendor, agents, inventory = (
        value["requires"],
        value["vendor"],
        value["agents"],
        value["inventory"],
    )
    if value["name"] != "raptor" or value["version"] != "1.0.0":
        raise BootstrapError("RAPTOR.BOOTSTRAP.MANIFEST: invalid identity")
    if requires != {
        "python": ">=3.11",
        "pydantic": PYDANTIC_CONSTRAINT,
        "cli": [
            {
                "name": "sc-compose",
                "version": ">=1.6.1,<2.0.0",
                "version_command": ["sc-compose", "--version"],
            }
        ],
    }:
        raise BootstrapError("RAPTOR.BOOTSTRAP.MANIFEST: invalid requirements")
    vendor_keys = {
        "algorithm",
        "tree_sha256",
        "canonical_schema_version",
        "package_version",
        "inventory",
    }
    if not isinstance(vendor, dict) or set(vendor) != vendor_keys:
        raise BootstrapError("RAPTOR.BOOTSTRAP.MANIFEST: invalid vendor metadata")
    if (
        vendor["algorithm"] != TREE_ALGORITHM
        or vendor["canonical_schema_version"] != SCHEMA_VERSION
        or vendor["package_version"] != SCHEMA_VERSION
    ):
        raise BootstrapError("RAPTOR.BOOTSTRAP.MANIFEST: unsupported vendor authority")
    if (
        not isinstance(vendor["tree_sha256"], str)
        or re.fullmatch(r"[0-9a-f]{64}", vendor["tree_sha256"]) is None
    ):
        raise BootstrapError("RAPTOR.BOOTSTRAP.MANIFEST: invalid vendor hash")
    if (
        not isinstance(agents, dict)
        or set(agents) != AGENTS
        or any(
            type(item) is not str or re.fullmatch(r"[0-9a-f]{64}", item) is None
            for item in agents.values()
        )
    ):
        raise BootstrapError("RAPTOR.BOOTSTRAP.MANIFEST: invalid agent inventory")
    for items in (inventory, vendor["inventory"]):
        if not isinstance(items, list) or any(type(item) is not str for item in items):
            raise BootstrapError("RAPTOR.BOOTSTRAP.MANIFEST: invalid file inventory")
        if items != sorted(set(items)) or any(
            PurePosixPath(item).is_absolute() or ".." in PurePosixPath(item).parts
            for item in items
        ):
            raise BootstrapError("RAPTOR.BOOTSTRAP.MANIFEST: invalid file inventory")
    return cast(dict[str, Any], value)


def bootstrap(plugin_root: Path | None = None) -> ModuleType:
    root = (plugin_root or Path(__file__).resolve().parents[1]).resolve()
    manifest = _manifest((root / "plugin-manifest.json").read_text(encoding="utf-8"))
    if manifest["inventory"] != _plugin_inventory(root):
        raise BootstrapError("RAPTOR.BOOTSTRAP.MANIFEST: packaged inventory differs")
    try:
        registry = parse_registry(
            (root / "agents/registry.yaml").read_text(encoding="utf-8")
        )
        for name, entry in registry["agents"].items():
            body = (root / entry["path"]).read_bytes()
            digest = hashlib.sha256(body).hexdigest()
            frontmatter = body.decode("utf-8").split("---\n", 2)[1]
            if (
                digest != entry["sha256"]
                or digest != manifest["agents"][name]
                or f"name: {name}\n" not in frontmatter
                or f"version: {entry['version']}\n" not in frontmatter
            ):
                raise ValueError("agent registry differs")
    except (IndexError, KeyError, OSError, UnicodeError, ValueError) as error:
        raise BootstrapError(
            "RAPTOR.BOOTSTRAP.REGISTRY: invalid agent registry"
        ) from error
    live = (root / "_vendor/raptor_schema").resolve()
    digest, inventory = tree_hash(live)
    vendor = manifest.get("vendor", {})
    if digest != vendor.get("tree_sha256") or inventory != vendor.get("inventory"):
        raise BootstrapError(
            "RAPTOR.BOOTSTRAP.VENDOR_HASH: vendored schema is not verified"
        )
    try:
        pydantic_version = version("pydantic")
    except PackageNotFoundError as error:
        raise BootstrapError(
            "RAPTOR.BOOTSTRAP.DEPENDENCY: install pydantic>=2.10,<3; see installation troubleshooting"
        ) from error
    if (
        sys.version_info < (3, 11)
        or manifest.get("requires", {}).get("python") != ">=3.11"
        or not _pydantic_compatible(pydantic_version)
        or manifest.get("requires", {}).get("pydantic") != PYDANTIC_CONSTRAINT
    ):
        raise BootstrapError(
            "RAPTOR.BOOTSTRAP.DEPENDENCY: incompatible Pydantic version"
        )
    prior = {
        name: module
        for name, module in tuple(sys.modules.items())
        if name == "raptor_schema" or name.startswith("raptor_schema.")
    }
    for module in prior.values():
        try:
            origin_value = module.__file__
            if not isinstance(origin_value, str):
                raise TypeError("module origin is not a path")
            origin = Path(origin_value).resolve()
        except (AttributeError, OSError, TypeError) as error:
            raise BootstrapError(
                "RAPTOR.BOOTSTRAP.PRECEDENCE: preloaded schema has no verified origin"
            ) from error
        if not origin.is_file() or live not in origin.parents:
            raise BootstrapError(
                "RAPTOR.BOOTSTRAP.PRECEDENCE: raptor_schema is already loaded from another path"
            )
    for name in prior:
        sys.modules.pop(name, None)
    vendor_root = str(live.parent)
    sys.path.insert(0, vendor_root)
    try:
        module = importlib.import_module("raptor_schema")
    except Exception:
        for name in tuple(sys.modules):
            if name == "raptor_schema" or name.startswith("raptor_schema."):
                sys.modules.pop(name, None)
        sys.modules.update(prior)
        raise
    module_path = Path(module.__file__ or "").resolve()
    if live not in module_path.parents:
        raise BootstrapError(
            "RAPTOR.BOOTSTRAP.PRECEDENCE: vendored runtime did not win import resolution"
        )
    storage = importlib.import_module("raptor_schema.storage.sqlite")
    if getattr(storage, "MODEL_SCHEMA_VERSION", None) != SCHEMA_VERSION or vendor.get(
        "package_version"
    ) != getattr(storage, "MODEL_SCHEMA_VERSION", None):
        raise BootstrapError(
            "RAPTOR.BOOTSTRAP.VERSION: schema or package version mismatch"
        )
    return module


__all__ = ["BootstrapError", "bootstrap"]
