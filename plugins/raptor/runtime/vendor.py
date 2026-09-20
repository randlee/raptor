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

from .io import atomic_json, fsync_directory, fsync_tree
from .registry import parse_registry

TREE_ALGORITHM = "sha256:path-nul-bytes-nul:v1"
PYDANTIC_CONSTRAINT = ">=2.10,<3"
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


def _sidecars(plugin_root: Path, transaction_id: str) -> tuple[Path, Path, Path, Path]:
    return (
        plugin_root / f"agents/registry.yaml.stage.{transaction_id}",
        plugin_root / f"agents/registry.yaml.backup.{transaction_id}",
        plugin_root / f"plugin-manifest.json.stage.{transaction_id}",
        plugin_root / f"plugin-manifest.json.backup.{transaction_id}",
    )


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
        "pre_registry_sha256",
        "post_registry_sha256",
        "pre_manifest_sha256",
        "post_manifest_sha256",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise VendorError("RAPTOR.VENDOR.RECOVERY", "invalid transaction marker schema")
    transaction_id = value["transaction_id"]
    if not isinstance(transaction_id, str) or not re.fullmatch(
        r"[0-9a-f]{32}", transaction_id
    ):
        raise VendorError("RAPTOR.VENDOR.RECOVERY", "invalid transaction identifier")
    states = {
        "prepared",
        "live_backed_up",
        "staged_promoted",
        "registry_promoted",
        "manifest_promoted",
        "verified",
        "complete",
    }
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
    for key in (
        "pre_registry_sha256",
        "post_registry_sha256",
        "pre_manifest_sha256",
        "post_manifest_sha256",
    ):
        item = value[key]
        if not isinstance(item, str) or not re.fullmatch(r"[0-9a-f]{64}", item):
            raise VendorError("RAPTOR.VENDOR.RECOVERY", "invalid sidecar hash")
    live, stage, backup, expected_marker, expected_lock = _expected_paths(
        plugin_root, transaction_id
    )
    expected = tuple(str(path.resolve()) for path in (live, stage, backup))
    recorded = (value["live_path"], value["stage_path"], value["backup_path"])
    if marker != expected_marker or lock != expected_lock or recorded != expected:
        raise VendorError("RAPTOR.VENDOR.RECOVERY", "marker paths are not canonical")
    return value, live, stage, backup


def _recover_impl(
    plugin_root: Path, marker: Path, lock: Path, *, force_restore: bool = False
) -> None:
    value, live, stage, backup = _validated_marker(plugin_root, marker, lock)
    registry_stage, registry_backup, manifest_stage, manifest_backup = _sidecars(
        plugin_root, value["transaction_id"]
    )
    registry = plugin_root / "agents/registry.yaml"
    manifest = plugin_root / "plugin-manifest.json"
    pre = (
        value["pre_tree_sha256"],
        value["pre_registry_sha256"],
        value["pre_manifest_sha256"],
    )
    post = (
        value["post_tree_sha256"],
        value["post_registry_sha256"],
        value["post_manifest_sha256"],
    )
    current = (
        _hash_or_none(live),
        _file_hash(registry),
        _file_hash(manifest),
    )
    if value["state"] == "complete":
        expected = post if value["outcome"] == "promoted" else pre
        if current != expected:
            raise VendorError(
                "RAPTOR.VENDOR.RECOVERY", "terminal marker does not match publication"
            )
    else:
        sidecar_hashes = {
            stage: post[0],
            backup: pre[0],
            registry_stage: post[1],
            registry_backup: pre[1],
            manifest_stage: post[2],
            manifest_backup: pre[2],
        }
        for path, expected_hash in sidecar_hashes.items():
            if path.exists():
                actual_hash = _hash_or_none(path) if path.is_dir() else _file_hash(path)
                if actual_hash != expected_hash:
                    raise VendorError(
                        "RAPTOR.VENDOR.RECOVERY", "transaction sidecar hash mismatch"
                    )
        if (
            not registry_backup.is_file()
            or not manifest_backup.is_file()
            or (
                pre[0] is not None
                and _hash_or_none(backup) != pre[0]
                and _hash_or_none(live) != pre[0]
            )
        ):
            raise VendorError(
                "RAPTOR.VENDOR.RECOVERY", "required rollback sidecar is missing"
            )
        post_sources = (
            live if _hash_or_none(live) == post[0] else stage,
            registry if _file_hash(registry) == post[1] else registry_stage,
            manifest if _file_hash(manifest) == post[2] else manifest_stage,
        )
        pre_sources = (
            live if _hash_or_none(live) == pre[0] else backup,
            registry if _file_hash(registry) == pre[1] else registry_backup,
            manifest if _file_hash(manifest) == pre[2] else manifest_backup,
        )
        can_promote = (
            _hash_or_none(post_sources[0]) == post[0]
            and post_sources[1].is_file()
            and _file_hash(post_sources[1]) == post[1]
            and post_sources[2].is_file()
            and _file_hash(post_sources[2]) == post[2]
        )
        can_restore = (
            (pre[0] is None or _hash_or_none(pre_sources[0]) == pre[0])
            and pre_sources[1].is_file()
            and _file_hash(pre_sources[1]) == pre[1]
            and pre_sources[2].is_file()
            and _file_hash(pre_sources[2]) == pre[2]
        )
        if not can_promote and not can_restore:
            raise VendorError(
                "RAPTOR.VENDOR.RECOVERY",
                "no complete publication triplet is recoverable",
            )
        preserve_pre = force_restore or value["state"] == "prepared"
        if preserve_pre and not can_restore:
            raise VendorError(
                "RAPTOR.VENDOR.RECOVERY",
                "verified rollback triplet is unavailable",
            )
        promote = can_promote and not preserve_pre
        desired = post if promote else pre
        sources = post_sources if promote else pre_sources
        _reconcile_triplet(
            marker,
            value,
            sources,
            desired,
            post,
            live,
            registry,
            manifest,
        )
        _write_marker(
            marker, value, "complete", "promoted" if promote else "restored"
        )
    _remove(stage)
    _remove(backup)
    _remove(registry_stage)
    _remove(registry_backup)
    _remove(manifest_stage)
    _remove(manifest_backup)
    _remove(marker)
    _remove(lock)


def _reconcile_triplet(
    marker: Path,
    value: dict[str, Any],
    sources: tuple[Path, Path, Path],
    desired: tuple[str | None, str, str],
    post: tuple[str | None, str, str],
    live: Path,
    registry: Path,
    manifest: Path,
) -> None:
    transaction_id = value["transaction_id"]
    vendor_sibling = live.parent / f"raptor_schema.recover.{transaction_id}"
    registry_sibling = registry.parent / f"registry.yaml.recover.{transaction_id}"
    manifest_sibling = (
        manifest.parent / f"plugin-manifest.json.recover.{transaction_id}"
    )
    for path in (vendor_sibling, registry_sibling, manifest_sibling):
        _remove(path)
    if desired[0] is not None:
        shutil.copytree(sources[0], vendor_sibling)
        fsync_tree(vendor_sibling)
    shutil.copy2(sources[1], registry_sibling)
    shutil.copy2(sources[2], manifest_sibling)
    for path in (registry_sibling, manifest_sibling):
        with path.open("rb") as stream:
            os.fsync(stream.fileno())
        fsync_directory(path.parent)
    if desired[0] is None:
        _remove(live)
    elif _hash_or_none(live) != desired[0]:
        _remove(live)
        os.replace(vendor_sibling, live)
        fsync_directory(live.parent)
    if desired == post and value["state"] in {"prepared", "live_backed_up"}:
        _write_marker(marker, value, "staged_promoted")
    os.replace(registry_sibling, registry)
    fsync_directory(registry.parent)
    if desired == post and value["state"] == "staged_promoted":
        _write_marker(marker, value, "registry_promoted")
    os.replace(manifest_sibling, manifest)
    fsync_directory(manifest.parent)
    if desired == post and value["state"] == "registry_promoted":
        _write_marker(marker, value, "manifest_promoted")
    actual = (_hash_or_none(live), _file_hash(registry), _file_hash(manifest))
    if actual != desired:
        raise VendorError(
            "RAPTOR.VENDOR.RECOVERY",
            "reconciled publication triplet failed verification",
        )
    if desired == post and value["state"] in {"manifest_promoted", "verified"}:
        _write_marker(marker, value, "verified")
    for path in (vendor_sibling, registry_sibling, manifest_sibling):
        _remove(path)


def _recover(
    plugin_root: Path, marker: Path, lock: Path, *, force_restore: bool = False
) -> None:
    try:
        _recover_impl(plugin_root, marker, lock, force_restore=force_restore)
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
                stale_id = owner.get("transaction_id")
                if (
                    not isinstance(stale_id, str)
                    or re.fullmatch(r"[0-9a-f]{32}", stale_id) is None
                ):
                    raise VendorError(
                        "RAPTOR.VENDOR.LOCKED", "stale lock has no valid transaction"
                    ) from error
                stale_live, stale_stage, stale_backup, _, stale_lock = _expected_paths(
                    plugin_root, stale_id
                )
                if stale_backup.exists() or not stale_live.exists():
                    raise VendorError(
                        "RAPTOR.VENDOR.RECOVERY",
                        "unmarked publication may have started",
                    ) from error
                _remove(stale_stage)
                for sidecar in _sidecars(plugin_root, stale_id):
                    _remove(sidecar)
                _remove(stale_lock)
                return _acquire(plugin_root, transaction_id)
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


def _registry_with_hashes(plugin_root: Path) -> tuple[dict[str, Any], dict[str, str]]:
    registry_path = plugin_root / "agents/registry.yaml"
    registry = parse_registry(registry_path.read_text(encoding="utf-8"))
    hashes: dict[str, str] = {}
    for name, entry in sorted(registry["agents"].items()):
        path = (plugin_root / entry["path"]).resolve()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        entry["sha256"] = digest
        hashes[name] = digest
    return registry, hashes


def _agent_hashes(plugin_root: Path) -> dict[str, str]:
    registry, hashes = _registry_with_hashes(plugin_root)
    current = parse_registry(
        (plugin_root / "agents/registry.yaml").read_text(encoding="utf-8")
    )
    if current != registry:
        raise VendorError("RAPTOR.VENDOR.DRIFT", "registry agent hash differs")
    return hashes


def _plugin_inventory(plugin_root: Path) -> list[str]:
    transaction = re.compile(
        r"(?:_vendor/raptor_schema\.(?:stage|backup|recover)\.[0-9a-f]{32}(?:/.*)?|"
        r"agents/registry\.yaml\.(?:stage|backup)\.[0-9a-f]{32}|"
        r"agents/registry\.yaml\.recover\.[0-9a-f]{32}|"
        r"plugin-manifest\.json\.(?:stage|backup|recover)\.[0-9a-f]{32}|"
        r"_vendor/raptor_schema-refresh\.json|_vendor/\.raptor_schema-refresh\.lock)"
    )
    return sorted(
        [
            path.relative_to(plugin_root).as_posix()
            for path in plugin_root.rglob("*")
            if path.is_file()
            if path.relative_to(plugin_root).as_posix() != "plugin-manifest.json"
            and not path.relative_to(plugin_root).as_posix().startswith("tests/")
            and transaction.fullmatch(path.relative_to(plugin_root).as_posix()) is None
        ]
    )


def refresh(plugin_root: Path, *, fail_at: str | None = None) -> dict[str, Any]:
    plugin_root = plugin_root.resolve()
    local_artifacts = [
        path
        for path in plugin_root.rglob("*")
        if path.name == "__pycache__" or path.suffix.casefold() in {".pyc", ".pyo"}
    ]
    if local_artifacts:
        raise VendorError(
            "RAPTOR.VENDOR.INVENTORY",
            "remove generated bytecode before refreshing packaged inventory",
        )
    repo_root = plugin_root.parents[1]
    transaction_id = uuid.uuid4().hex
    live, stage, backup, marker, lock = _expected_paths(plugin_root, transaction_id)
    registry_stage, registry_backup, manifest_stage, manifest_backup = _sidecars(
        plugin_root, transaction_id
    )
    registry_path = plugin_root / "agents/registry.yaml"
    manifest_path = plugin_root / "plugin-manifest.json"
    lock = _acquire(plugin_root, transaction_id)

    def checkpoint(name: str) -> None:
        if fail_at == name:
            raise RuntimeError(f"injected failure: {name}")

    try:
        _copy_source(repo_root, stage)
        fsync_tree(stage)
        fsync_directory(stage.parent)
        post_hash, inventory = tree_hash(stage)
        with tempfile.TemporaryDirectory(dir=live.parent) as verification_directory:
            verification = Path(verification_directory) / "raptor_schema"
            _copy_source(repo_root, verification)
            if tree_hash(verification) != (post_hash, inventory):
                raise VendorError(
                    "RAPTOR.VENDOR.RECOVERY", "staged tree differs from source"
                )
        pre_hash = _hash_or_none(live)
        registry, hashes = _registry_with_hashes(plugin_root)
        atomic_json(registry_stage, registry, indent=2)
        checkpoint("after_registry_stage")
        package_version, python_constraint, pydantic_constraint = _schema_metadata(
            repo_root
        )
        publication = {
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
            "agents": hashes,
            "inventory": _plugin_inventory(plugin_root),
        }
        atomic_json(manifest_stage, publication, indent=2)
        checkpoint("after_manifest_stage")
        shutil.copy2(registry_path, registry_backup)
        with registry_backup.open("rb") as stream:
            os.fsync(stream.fileno())
        fsync_directory(registry_backup.parent)
        checkpoint("after_registry_backup")
        shutil.copy2(manifest_path, manifest_backup)
        with manifest_backup.open("rb") as stream:
            os.fsync(stream.fileno())
        fsync_directory(manifest_backup.parent)
        checkpoint("after_manifest_backup")
        value: dict[str, Any] = {
            "transaction_id": transaction_id,
            "pre_tree_sha256": pre_hash,
            "post_tree_sha256": post_hash,
            "live_path": str(live.resolve()),
            "stage_path": str(stage.resolve()),
            "backup_path": str(backup.resolve()),
            "outcome": "pending",
            "pre_registry_sha256": _file_hash(registry_backup),
            "post_registry_sha256": _file_hash(registry_stage),
            "pre_manifest_sha256": _file_hash(manifest_backup),
            "post_manifest_sha256": _file_hash(manifest_stage),
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
        fsync_tree(live)
        fsync_directory(live.parent)
        checkpoint("after_stage_rename")
        _write_marker(marker, value, "staged_promoted")
        checkpoint("after_staged_promoted")
        if tree_hash(live)[0] != post_hash:
            raise VendorError("RAPTOR.VENDOR.RECOVERY", "promoted tree hash mismatch")
        os.replace(registry_stage, registry_path)
        fsync_directory(registry_path.parent)
        _write_marker(marker, value, "registry_promoted")
        checkpoint("after_registry_promoted")
        os.replace(manifest_stage, manifest_path)
        fsync_directory(manifest_path.parent)
        _write_marker(marker, value, "manifest_promoted")
        checkpoint("after_manifest_promoted")
        check(plugin_root)
        _write_marker(marker, value, "verified")
        checkpoint("after_final_check")
        fsync_tree(live)
        fsync_directory(live.parent)
        _write_marker(marker, value, "complete", "promoted")
        checkpoint("after_complete")
        _remove(backup)
        _remove(registry_backup)
        _remove(manifest_backup)
        _remove(marker)
        _remove(lock)
        return publication
    except Exception as error:
        if fail_at is None and marker.exists():
            try:
                _recover(plugin_root, marker, lock, force_restore=True)
            except VendorError as recovery_error:
                raise recovery_error from error
        elif fail_at is None:
            _remove(stage)
            _remove(registry_stage)
            _remove(registry_backup)
            _remove(manifest_stage)
            _remove(manifest_backup)
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
