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
        "after_complete",
    ],
)
def test_restart_recovery_at_every_boundary(tmp_path: Path, boundary: str) -> None:
    plugin = sandbox(tmp_path)
    with pytest.raises(RuntimeError, match="injected failure"):
        refresh(plugin, fail_at=boundary)
    lock = plugin / "_vendor/.raptor_schema-refresh.lock"
    value = json.loads(lock.read_text())
    value["pid"] = 99999999
    lock.write_text(json.dumps(value))
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

    def corrupt(marker: Path, value: dict[str, object], state: str) -> None:
        original(marker, value, state)
        if state == "staged_promoted":
            live = Path(value["live_path"])
            (live / "canonical.py").write_text("corrupt", encoding="utf-8")

    monkeypatch.setattr(vendor, "_write_marker", corrupt)
    with pytest.raises(VendorError, match="VERIFY"):
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
