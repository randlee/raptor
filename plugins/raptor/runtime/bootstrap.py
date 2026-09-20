from __future__ import annotations

import importlib
import json
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from types import ModuleType

from .vendor import PACKAGE_VERSION, PYDANTIC_CONSTRAINT, SCHEMA_VERSION, tree_hash


class BootstrapError(RuntimeError):
    pass


def _pydantic_compatible(actual: str) -> bool:
    major, minor, *_ = (int(part) for part in actual.split(".") if part.isdigit())
    return major == 2 and minor >= 10


def bootstrap(plugin_root: Path | None = None) -> ModuleType:
    root = (plugin_root or Path(__file__).resolve().parents[1]).resolve()
    manifest = json.loads((root / "plugin-manifest.json").read_text(encoding="utf-8"))
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
    loaded = sys.modules.get("raptor_schema")
    if loaded is not None:
        loaded_path = Path(getattr(loaded, "__file__", "")).resolve()
        if live not in loaded_path.parents:
            raise BootstrapError(
                "RAPTOR.BOOTSTRAP.PRECEDENCE: raptor_schema is already loaded from another path"
            )
        return loaded
    vendor_root = str(live.parent)
    sys.path.insert(0, vendor_root)
    module = importlib.import_module("raptor_schema")
    module_path = Path(module.__file__ or "").resolve()
    if live not in module_path.parents:
        raise BootstrapError(
            "RAPTOR.BOOTSTRAP.PRECEDENCE: vendored runtime did not win import resolution"
        )
    storage = importlib.import_module("raptor_schema.storage.sqlite")
    if (
        getattr(storage, "MODEL_SCHEMA_VERSION", None) != SCHEMA_VERSION
        or vendor.get("package_version") != PACKAGE_VERSION
    ):
        raise BootstrapError(
            "RAPTOR.BOOTSTRAP.VERSION: schema or package version mismatch"
        )
    return module


__all__ = ["BootstrapError", "bootstrap"]
