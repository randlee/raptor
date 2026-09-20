from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import tomllib
import uuid
from pathlib import Path
from typing import Any

from .io import atomic_json, fsync_directory

TREE_ALGORITHM = "sha256:path-nul-bytes-nul:v1"
PYTHON_CONSTRAINT = ">=3.11"
PYDANTIC_CONSTRAINT = ">=2.10,<3"
PACKAGE_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0.0"


class VendorError(RuntimeError):
    def __init__(self, code: str, message: str, *, outcome: str = "failed") -> None:
        self.code = code
        self.outcome = outcome
        super().__init__(f"{code}: {message}; outcome={outcome}")


def _files(root: Path) -> list[Path]:
    return sorted(
        (
            path
            for path in root.rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and path.suffix not in {".pyc", ".pyo"}
            and not path.name.startswith(".DS_Store")
        ),
        key=lambda path: path.relative_to(root).as_posix(),
    )


def tree_hash(root: Path) -> tuple[str, list[str]]:
    digest = hashlib.sha256()
    inventory: list[str] = []
    for path in _files(root):
        relative = path.relative_to(root).as_posix()
        inventory.append(relative)
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest(), inventory


def _expected_paths(
    plugin_root: Path, transaction_id: str
) -> tuple[Path, Path, Path, Path, Path]:
    vendor_root = plugin_root / "_vendor"
    return (
        vendor_root / "raptor_schema",
        vendor_root / f"raptor_schema.stage.{transaction_id}",
        vendor_root / f"raptor_schema.backup.{transaction_id}",
        vendor_root / "raptor_schema-refresh.json",
        vendor_root / ".raptor_schema-refresh.lock",
    )


def _remove(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def _hash_or_none(path: Path) -> str | None:
    return tree_hash(path)[0] if path.is_dir() else None


def _write_marker(
    marker: Path, value: dict[str, Any], state: str, outcome: str = "pending"
) -> None:
    value["state"] = state
    value["outcome"] = outcome
    atomic_json(marker, value, indent=2)


def _validated_marker(
    plugin_root: Path, marker: Path, lock: Path
) -> tuple[dict[str, Any], Path, Path, Path]:
    try:
        value = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise VendorError(
            "RAPTOR.VENDOR.RECOVERY", "malformed transaction marker"
        ) from error
    required = {
        "transaction_id",
        "pre_tree_sha256",
        "post_tree_sha256",
        "live_path",
        "stage_path",
        "backup_path",
        "state",
        "outcome",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise VendorError("RAPTOR.VENDOR.RECOVERY", "invalid transaction marker schema")
    transaction_id = value["transaction_id"]
    if not isinstance(transaction_id, str) or not re.fullmatch(
        r"[0-9a-f]{32}", transaction_id
    ):
        raise VendorError("RAPTOR.VENDOR.RECOVERY", "invalid transaction identifier")
    states = {"prepared", "live_backed_up", "staged_promoted", "complete"}
    outcomes = {"pending", "promoted", "preserved", "restored"}
    if value["state"] not in states or value["outcome"] not in outcomes:
        raise VendorError("RAPTOR.VENDOR.RECOVERY", "unknown transaction state")
    if (value["state"] == "complete") != (value["outcome"] != "pending"):
        raise VendorError("RAPTOR.VENDOR.RECOVERY", "inconsistent terminal marker")
    post = value["post_tree_sha256"]
    if not isinstance(post, str) or not re.fullmatch(r"[0-9a-f]{64}", post):
        raise VendorError("RAPTOR.VENDOR.RECOVERY", "invalid transaction hash")
    pre = value["pre_tree_sha256"]
    if pre is not None and (
        not isinstance(pre, str) or not re.fullmatch(r"[0-9a-f]{64}", pre)
    ):
        raise VendorError("RAPTOR.VENDOR.RECOVERY", "invalid transaction hash")
    live, stage, backup, expected_marker, expected_lock = _expected_paths(
        plugin_root, transaction_id
    )
    expected = tuple(str(path.resolve()) for path in (live, stage, backup))
    recorded = (value["live_path"], value["stage_path"], value["backup_path"])
    if marker != expected_marker or lock != expected_lock or recorded != expected:
        raise VendorError("RAPTOR.VENDOR.RECOVERY", "marker paths are not canonical")
    return value, live, stage, backup


def _recover_impl(plugin_root: Path, marker: Path, lock: Path) -> None:
    value, live, stage, backup = _validated_marker(plugin_root, marker, lock)
    pre_hash = value.get("pre_tree_sha256")
    post_hash = value.get("post_tree_sha256")
    state = value.get("state")
    live_hash, stage_hash, backup_hash = map(_hash_or_none, (live, stage, backup))
    if state == "complete":
        expected = post_hash if value["outcome"] == "promoted" else pre_hash
        if live_hash != expected:
            raise VendorError(
                "RAPTOR.VENDOR.RECOVERY", "terminal marker does not match live tree"
            )
    elif live_hash == post_hash:
        _write_marker(marker, value, "complete", "promoted")
    elif state == "prepared" and (
        live_hash == pre_hash or (pre_hash is None and live_hash is None)
    ):
        _write_marker(marker, value, "complete", "preserved")
    elif state == "prepared" and backup_hash == pre_hash and live_hash is None:
        backup.rename(live)
        fsync_directory(live.parent)
        _write_marker(marker, value, "complete", "restored")
    elif stage_hash == post_hash and state in {"live_backed_up", "staged_promoted"}:
        if live.exists():
            raise VendorError(
                "RAPTOR.VENDOR.RECOVERY", "ambiguous live and staged trees"
            )
        stage.rename(live)
        fsync_directory(live.parent)
        _write_marker(marker, value, "complete", "promoted")
    elif backup_hash == pre_hash and state in {
        "live_backed_up",
        "staged_promoted",
        "complete",
    }:
        _remove(live)
        backup.rename(live)
        fsync_directory(live.parent)
        _write_marker(marker, value, "complete", "restored")
    else:
        raise VendorError("RAPTOR.VENDOR.RECOVERY", "hash/state disagreement")
    final_hash = _hash_or_none(live)
    if final_hash not in {pre_hash, post_hash}:
        raise VendorError(
            "RAPTOR.VENDOR.RECOVERY", "recovery did not produce a verified live tree"
        )
    _remove(stage)
    _remove(backup)
    _remove(marker)
    _remove(lock)


def _recover(plugin_root: Path, marker: Path, lock: Path) -> None:
    try:
        _recover_impl(plugin_root, marker, lock)
    except VendorError:
        raise
    except Exception as error:
        raise VendorError(
            "RAPTOR.VENDOR.RECOVERY", "recovery operation failed"
        ) from error


def _acquire(plugin_root: Path, transaction_id: str) -> Path:
    *_, marker, lock = _expected_paths(plugin_root, transaction_id)
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        try:
            owner = json.loads(lock.read_text(encoding="utf-8"))
            owner_pid = int(owner["pid"])
            os.kill(owner_pid, 0)
        except ProcessLookupError:
            if not marker.exists():
                raise VendorError(
                    "RAPTOR.VENDOR.LOCKED", "stale lock has no matching marker"
                ) from error
            try:
                marker_value = json.loads(marker.read_text(encoding="utf-8"))
                matches = owner.get("transaction_id") == marker_value["transaction_id"]
            except (OSError, KeyError, TypeError, json.JSONDecodeError) as invalid:
                raise VendorError(
                    "RAPTOR.VENDOR.RECOVERY", "malformed stale transaction marker"
                ) from invalid
            if not matches:
                raise VendorError(
                    "RAPTOR.VENDOR.LOCKED", "stale lock has no matching marker"
                ) from error
            _recover(plugin_root, marker, lock)
            return _acquire(plugin_root, transaction_id)
        except (KeyError, ValueError, OSError, json.JSONDecodeError) as invalid:
            raise VendorError(
                "RAPTOR.VENDOR.LOCKED", "invalid or live lock"
            ) from invalid
        raise VendorError(
            "RAPTOR.VENDOR.LOCKED", "refresh is already running"
        ) from error
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump({"pid": os.getpid(), "transaction_id": transaction_id}, stream)
        stream.flush()
        os.fsync(stream.fileno())
    fsync_directory(lock.parent)
    return lock


def _copy_source(repo_root: Path, stage: Path) -> None:
    source = repo_root / "schema/src/raptor_schema"
    shutil.copytree(
        source,
        stage,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".DS_Store"),
    )
    ddl_target = stage / "sql/sqlite"
    ddl_target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        repo_root / "schema/sql/sqlite/0001_initial.sql",
        ddl_target / "0001_initial.sql",
    )


def _schema_metadata(repo_root: Path) -> tuple[str, str, str]:
    with (repo_root / "schema/pyproject.toml").open("rb") as stream:
        project = tomllib.load(stream)["project"]
    pydantic = next(
        dependency.removeprefix("pydantic")
        for dependency in project["dependencies"]
        if dependency.startswith("pydantic")
    )
    return project["version"], project["requires-python"], pydantic


def _agent_hashes(plugin_root: Path, *, update: bool = False) -> dict[str, str]:
    registry_path = plugin_root / "agents/registry.yaml"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    hashes: dict[str, str] = {}
    for name, entry in sorted(registry["agents"].items()):
        path = (plugin_root / entry["path"]).resolve()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if not update and entry.get("sha256") != digest:
            raise VendorError("RAPTOR.VENDOR.DRIFT", "registry agent hash differs")
        entry["sha256"] = digest
        hashes[name] = digest
    if update:
        atomic_json(registry_path, registry, indent=2)
    return hashes


def _plugin_inventory(plugin_root: Path) -> list[str]:
    excluded = {"plugin-manifest.json"}
    return [
        path.relative_to(plugin_root).as_posix()
        for path in _files(plugin_root)
        if path.relative_to(plugin_root).as_posix() not in excluded
        and not path.relative_to(plugin_root).as_posix().startswith("tests/")
        and ".stage." not in path.as_posix()
        and ".backup." not in path.as_posix()
        and "refresh" not in path.name
    ]


def refresh(plugin_root: Path, *, fail_at: str | None = None) -> dict[str, Any]:
    plugin_root = plugin_root.resolve()
    repo_root = plugin_root.parents[1]
    transaction_id = uuid.uuid4().hex
    live, stage, backup, marker, lock = _expected_paths(plugin_root, transaction_id)
    lock = _acquire(plugin_root, transaction_id)

    def checkpoint(name: str) -> None:
        if fail_at == name:
            raise RuntimeError(f"injected failure: {name}")

    try:
        _copy_source(repo_root, stage)
        post_hash, inventory = tree_hash(stage)
        with tempfile.TemporaryDirectory(dir=live.parent) as verification_directory:
            verification = Path(verification_directory) / "raptor_schema"
            _copy_source(repo_root, verification)
            if tree_hash(verification) != (post_hash, inventory):
                raise VendorError(
                    "RAPTOR.VENDOR.RECOVERY", "staged tree differs from source"
                )
        pre_hash = _hash_or_none(live)
        value: dict[str, Any] = {
            "transaction_id": transaction_id,
            "pre_tree_sha256": pre_hash,
            "post_tree_sha256": post_hash,
            "live_path": str(live.resolve()),
            "stage_path": str(stage.resolve()),
            "backup_path": str(backup.resolve()),
            "outcome": "pending",
        }
        _write_marker(marker, value, "prepared")
        checkpoint("after_prepared")
        if live.exists():
            live.rename(backup)
            fsync_directory(live.parent)
        checkpoint("after_live_rename")
        _write_marker(marker, value, "live_backed_up")
        checkpoint("after_live_backed_up")
        stage.rename(live)
        fsync_directory(live.parent)
        checkpoint("after_stage_rename")
        _write_marker(marker, value, "staged_promoted")
        checkpoint("after_staged_promoted")
        if tree_hash(live)[0] != post_hash:
            raise VendorError("RAPTOR.VENDOR.RECOVERY", "promoted tree hash mismatch")
        _write_marker(marker, value, "complete", "promoted")
        checkpoint("after_complete")
        package_version, python_constraint, pydantic_constraint = _schema_metadata(
            repo_root
        )
        manifest = {
            "name": "raptor",
            "version": "1.0.0",
            "requires": {"python": python_constraint, "pydantic": pydantic_constraint},
            "vendor": {
                "algorithm": TREE_ALGORITHM,
                "tree_sha256": post_hash,
                "canonical_schema_version": SCHEMA_VERSION,
                "package_version": package_version,
                "inventory": inventory,
            },
            "agents": _agent_hashes(plugin_root, update=True),
        }
        manifest["inventory"] = _plugin_inventory(plugin_root)
        atomic_json(plugin_root / "plugin-manifest.json", manifest, indent=2)
        check(plugin_root)
        _remove(backup)
        _remove(marker)
        _remove(lock)
        return manifest
    except Exception as error:
        if fail_at is None and marker.exists():
            try:
                _recover(plugin_root, marker, lock)
            except VendorError as recovery_error:
                raise recovery_error from error
        elif fail_at is None:
            _remove(stage)
            _remove(lock)
        if fail_at is not None or isinstance(error, VendorError):
            raise
        raise VendorError(
            "RAPTOR.VENDOR.RECOVERY",
            "refresh failed and was reconciled",
            outcome="reconciled",
        ) from error


def check(plugin_root: Path) -> None:
    plugin_root = plugin_root.resolve()
    repo_root = plugin_root.parents[1]
    with tempfile.TemporaryDirectory(dir=plugin_root / "_vendor") as directory:
        expected = Path(directory) / "raptor_schema"
        _copy_source(repo_root, expected)
        expected_hash, expected_inventory = tree_hash(expected)
    live = plugin_root / "_vendor/raptor_schema"
    live_hash, live_inventory = tree_hash(live)
    manifest = json.loads(
        (plugin_root / "plugin-manifest.json").read_text(encoding="utf-8")
    )
    vendor = manifest.get("vendor", {})
    package_version, python_constraint, pydantic_constraint = _schema_metadata(
        repo_root
    )
    if (
        live_hash != expected_hash
        or live_inventory != expected_inventory
        or vendor.get("tree_sha256") != expected_hash
        or vendor.get("inventory") != expected_inventory
        or vendor.get("algorithm") != TREE_ALGORITHM
        or vendor.get("canonical_schema_version") != SCHEMA_VERSION
        or vendor.get("package_version") != package_version
        or manifest.get("requires")
        != {"python": python_constraint, "pydantic": pydantic_constraint}
    ):
        raise VendorError("RAPTOR.VENDOR.DRIFT", "source, vendor, or metadata differs")
    if manifest.get("agents") != _agent_hashes(plugin_root):
        raise VendorError("RAPTOR.VENDOR.DRIFT", "agent inventory differs")
    if manifest.get("inventory") != _plugin_inventory(plugin_root):
        raise VendorError("RAPTOR.VENDOR.DRIFT", "plugin inventory differs")


__all__ = ["VendorError", "check", "refresh", "tree_hash"]
