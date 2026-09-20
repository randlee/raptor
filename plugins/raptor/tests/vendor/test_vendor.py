from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

from runtime import vendor
from runtime.vendor import VendorError, check, refresh

ROOT = Path(__file__).parents[2]
REPO = ROOT.parents[1]


def sandbox(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(REPO / "schema", root / "schema")
    shutil.copytree(
        ROOT,
        root / "plugins/raptor",
        ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyc"),
    )
    return root / "plugins/raptor"


def test_refresh_check_and_hand_edit_detection(tmp_path: Path) -> None:
    plugin = sandbox(tmp_path)
    refresh(plugin)
    check(plugin)
    (plugin / "_vendor/raptor_schema/canonical.py").write_text("tampered")
    with pytest.raises(VendorError, match="DRIFT"):
        check(plugin)


@pytest.mark.parametrize(
    "relative",
    [
        "_vendor/raptor_schema.stage.not-a-transaction/file.py",
        "agents/unrelated.backup.file",
        "runtime/refresh-notes.txt",
    ],
)
def test_inventory_rejects_every_noncanonical_extra(
    tmp_path: Path, relative: str
) -> None:
    plugin = sandbox(tmp_path)
    path = plugin / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("extra")
    with pytest.raises(VendorError, match="inventory"):
        check(plugin)


def test_live_lock_and_unmatched_stale_lock_fail(tmp_path: Path) -> None:
    plugin = sandbox(tmp_path)
    lock = plugin / "_vendor/.raptor_schema-refresh.lock"
    lock.parent.mkdir(exist_ok=True)
    lock.write_text(json.dumps({"pid": os.getpid(), "transaction_id": "live"}))
    with pytest.raises(VendorError, match="LOCKED"):
        refresh(plugin)
    lock.write_text(json.dumps({"pid": 99999999, "transaction_id": "stale"}))
    with pytest.raises(VendorError, match="stale lock"):
        refresh(plugin)


@pytest.mark.parametrize(
    "boundary",
    [
        "after_prepared",
        "after_live_rename",
        "after_live_backed_up",
        "after_stage_rename",
        "after_staged_promoted",
        "after_registry_promoted",
        "after_manifest_promoted",
        "after_final_check",
        "after_complete",
    ],
)
def test_restart_recovery_at_every_boundary(tmp_path: Path, boundary: str) -> None:
    plugin = sandbox(tmp_path)
    source = plugin.parents[1] / "schema/src/raptor_schema/canonical.py"
    source.write_text(source.read_text() + "\n# recovery publication\n")
    with pytest.raises(RuntimeError, match="injected failure"):
        refresh(plugin, fail_at=boundary)
    lock = plugin / "_vendor/.raptor_schema-refresh.lock"
    value = json.loads(lock.read_text())
    value["pid"] = 99999999
    lock.write_text(json.dumps(value))
    marker = plugin / "_vendor/raptor_schema-refresh.json"
    transaction = json.loads(marker.read_text())
    vendor._recover(plugin, marker, lock)
    assert (
        vendor.tree_hash(plugin / "_vendor/raptor_schema")[0]
        == transaction["post_tree_sha256"]
    )
    assert (
        vendor._file_hash(plugin / "agents/registry.yaml")
        == transaction["post_registry_sha256"]
    )
    assert (
        vendor._file_hash(plugin / "plugin-manifest.json")
        == transaction["post_manifest_sha256"]
    )
    refresh(plugin)
    check(plugin)


def test_vendor_is_deterministic(tmp_path: Path) -> None:
    plugin = sandbox(tmp_path)
    first = refresh(plugin)["vendor"]["tree_sha256"]
    second = refresh(plugin)["vendor"]["tree_sha256"]
    assert first == second


def test_promotion_verification_failure_restores_verified_backup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plugin = sandbox(tmp_path)
    refresh(plugin)
    before = vendor.tree_hash(plugin / "_vendor/raptor_schema")[0]
    original = vendor._write_marker

    def corrupt(
        marker: Path, value: dict[str, object], state: str, outcome: str = "pending"
    ) -> None:
        original(marker, value, state, outcome)
        if state == "staged_promoted":
            live = Path(value["live_path"])
            (live / "canonical.py").write_text("corrupt", encoding="utf-8")

    monkeypatch.setattr(vendor, "_write_marker", corrupt)
    with pytest.raises(VendorError, match="RECOVERY"):
        refresh(plugin)
    assert vendor.tree_hash(plugin / "_vendor/raptor_schema")[0] == before


def test_failure_before_marker_cleans_stage_and_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plugin = sandbox(tmp_path)

    def fail(repo_root: Path, stage: Path) -> None:
        raise OSError("copy failed")

    monkeypatch.setattr(vendor, "_copy_source", fail)
    with pytest.raises(VendorError, match="RECOVERY"):
        refresh(plugin)
    assert not (plugin / "_vendor/.raptor_schema-refresh.lock").exists()
    assert not list((plugin / "_vendor").glob("*.stage.*"))


@pytest.mark.parametrize("contents", ["not-json", "{}", '{"state":"unknown"}'])
def test_malformed_or_unknown_recovery_marker_fails_closed(
    tmp_path: Path, contents: str
) -> None:
    plugin = sandbox(tmp_path)
    lock = plugin / "_vendor/.raptor_schema-refresh.lock"
    marker = plugin / "_vendor/raptor_schema-refresh.json"
    lock.parent.mkdir(exist_ok=True)
    lock.write_text(json.dumps({"pid": 99999999, "transaction_id": "0" * 32}))
    marker.write_text(contents)
    with pytest.raises(VendorError, match="RECOVERY"):
        vendor._recover(plugin, marker, lock)
    assert lock.exists() and marker.exists()


@pytest.mark.parametrize(
    "boundary",
    [
        "after_registry_stage",
        "after_manifest_stage",
        "after_registry_backup",
        "after_manifest_backup",
    ],
)
def test_restart_discards_unpublished_sidecars(tmp_path: Path, boundary: str) -> None:
    plugin = sandbox(tmp_path)
    with pytest.raises(RuntimeError, match="injected failure"):
        refresh(plugin, fail_at=boundary)
    lock = plugin / "_vendor/.raptor_schema-refresh.lock"
    value = json.loads(lock.read_text())
    value["pid"] = 99999999
    lock.write_text(json.dumps(value))
    refresh(plugin)
    check(plugin)
    assert not list(plugin.rglob("*.stage.*")) and not list(plugin.rglob("*.backup.*"))


def test_sidecars_roll_forward_complete_publication_before_new_refresh(
    tmp_path: Path,
) -> None:
    plugin = sandbox(tmp_path)
    source = plugin.parents[1] / "schema/src/raptor_schema/canonical.py"
    source.write_text(source.read_text() + "\n# roll forward\n")
    with pytest.raises(RuntimeError):
        refresh(plugin, fail_at="after_manifest_promoted")
    lock = plugin / "_vendor/.raptor_schema-refresh.lock"
    owner = json.loads(lock.read_text())
    lock.write_text(json.dumps({**owner, "pid": 99999999}))
    marker = plugin / "_vendor/raptor_schema-refresh.json"
    transaction = json.loads(marker.read_text())
    vendor._recover(plugin, marker, lock)
    assert (
        vendor.tree_hash(plugin / "_vendor/raptor_schema")[0]
        == transaction["post_tree_sha256"]
    )
    assert (
        vendor._file_hash(plugin / "agents/registry.yaml")
        == transaction["post_registry_sha256"]
    )
    assert (
        vendor._file_hash(plugin / "plugin-manifest.json")
        == transaction["post_manifest_sha256"]
    )


def test_final_check_failure_reconciles_complete_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plugin = sandbox(tmp_path)
    source = plugin.parents[1] / "schema/src/raptor_schema/canonical.py"
    source.write_text(source.read_text() + "\n# final check reconcile\n")
    monkeypatch.setattr(
        vendor,
        "check",
        lambda root: (_ for _ in ()).throw(OSError("final check failed")),
    )
    with pytest.raises(VendorError, match="reconciled"):
        refresh(plugin)
    assert (
        "# final check reconcile"
        in (plugin / "_vendor/raptor_schema/canonical.py").read_text()
    )
    assert not list(plugin.rglob("*.stage.*")) and not list(plugin.rglob("*.backup.*"))


def test_fsync_precedes_completion_and_backup_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plugin = sandbox(tmp_path)
    events: list[str] = []
    original_sync, original_marker, original_remove = (
        vendor.fsync_tree,
        vendor._write_marker,
        vendor._remove,
    )

    def sync(path: Path) -> None:
        events.append(f"sync:{path.name}")
        original_sync(path)

    def mark(
        path: Path, value: dict[str, object], state: str, outcome: str = "pending"
    ) -> None:
        events.append(f"mark:{state}")
        original_marker(path, value, state, outcome)

    def remove(path: Path) -> None:
        if ".backup." in path.name:
            events.append("remove:backup")
        original_remove(path)

    monkeypatch.setattr(vendor, "fsync_tree", sync)
    monkeypatch.setattr(vendor, "_write_marker", mark)
    monkeypatch.setattr(vendor, "_remove", remove)
    refresh(plugin)
    stage_sync = next(
        index
        for index, event in enumerate(events)
        if event.startswith("sync:raptor_schema.stage.")
    )
    assert stage_sync < events.index("mark:prepared")
    assert events.index("sync:raptor_schema") < events.index("mark:complete")
    assert events.index("mark:complete") < events.index("remove:backup")
