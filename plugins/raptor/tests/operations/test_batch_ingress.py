from __future__ import annotations

import json
from pathlib import Path

import pytest
from raptor_schema import IngressReport, SQLiteArtifactStore

from runtime.operations import configured_markdown_to_sqlite


def _write_configuration(root: Path, *, registered: bool = True) -> None:
    (root / ".raptor").mkdir()
    (root / ".raptor/raptor.toml").write_text(
        """schema_version = "1.0.0"
repository_id = "urn:raptor:repo:sample"

[files]
scan = "sources.toml"
routing = "routing.toml"
identity = "identity.json"
"""
    )
    (root / ".raptor/sources.toml").write_text(
        """schema_version = "1.0.0"

[[sources]]
name = "requirements"
root = "specifications"
include = ["**/*.md"]
exclude = ["README.md"]
"""
    )
    (root / ".raptor/routing.toml").write_text(
        """schema_version = "1.0.0"

[[routes]]
source = "requirements"
artifact_types = ["requirement"]

[routes.profile]
profile_id = "raptor"
profile_version = "1.0.0"
"""
    )
    documents = (
        {"DOC-RAP-001": {"path": "specifications/requirements.md"}}
        if registered
        else {}
    )
    (root / ".raptor/identity.json").write_text(
        json.dumps(
            {
                "identity_version": "1.0.0",
                "repository_id": "urn:raptor:repo:sample",
                "documents": documents,
            }
        )
    )


def _repository(tmp_path: Path, *, registered: bool = True) -> Path:
    root = tmp_path / "repository"
    (root / "specifications").mkdir(parents=True)
    (root / "specifications/requirements.md").write_text(
        """### REQ-RAP-001 — Configured ingress
Use only configured source paths.
Acceptance: The report is deterministic.
"""
    )
    (root / "specifications/README.md").write_text("not an artifact\n")
    _write_configuration(root, registered=registered)
    return root


def test_configured_ingress_imports_only_authorized_registered_paths(tmp_path: Path) -> None:
    root = _repository(tmp_path)

    result = configured_markdown_to_sqlite(
        root,
        ".raptor/raptor.toml",
        ".raptor/state/ingress.sqlite",
        ".raptor/state/ingress-report.json",
        apply=True,
    )

    report = IngressReport.model_validate(result["report_data"])
    assert [(entry.repository_path, entry.outcome) for entry in report.entries] == [
        ("specifications/requirements.md", "imported")
    ]
    assert report.entries[0].sqlite_outcome == "persisted"
    assert (root / ".raptor/state/ingress-report.json").read_bytes().endswith(b"\n")
    store = SQLiteArtifactStore(root / ".raptor/state/ingress.sqlite")
    try:
        assert [key.document_id for key in store.list_document_keys()] == ["DOC-RAP-001"]
    finally:
        store.close()


def test_configured_ingress_validate_mode_is_deterministic(tmp_path: Path) -> None:
    root = _repository(tmp_path)

    first = configured_markdown_to_sqlite(
        root,
        ".raptor/raptor.toml",
        ".raptor/state/ingress.sqlite",
        ".raptor/state/ingress-report.json",
    )
    second = configured_markdown_to_sqlite(
        root,
        ".raptor/raptor.toml",
        ".raptor/state/ingress.sqlite",
        ".raptor/state/ingress-report.json",
    )

    assert first["report_data"] == second["report_data"]
    assert not (root / ".raptor/state/ingress.sqlite").exists()
    assert not (root / ".raptor/state/ingress-report.json").exists()


def test_configured_ingress_apply_reports_are_byte_identical(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    arguments = (
        root,
        ".raptor/raptor.toml",
        ".raptor/state/ingress.sqlite",
        ".raptor/state/ingress-report.json",
    )

    configured_markdown_to_sqlite(*arguments, apply=True)
    first = (root / ".raptor/state/ingress-report.json").read_bytes()
    configured_markdown_to_sqlite(*arguments, apply=True)
    second = (root / ".raptor/state/ingress-report.json").read_bytes()

    assert first == second


def test_unregistered_authorized_path_is_diagnosed_without_partial_apply(tmp_path: Path) -> None:
    root = _repository(tmp_path, registered=False)

    result = configured_markdown_to_sqlite(
        root,
        ".raptor/raptor.toml",
        ".raptor/state/ingress.sqlite",
        ".raptor/state/ingress-report.json",
        apply=True,
    )

    report = IngressReport.model_validate(result["report_data"])
    assert report.entries[0].outcome == "diagnosed"
    assert report.entries[0].diagnostic is not None
    assert report.entries[0].diagnostic.code == "RAPTOR.IDENTITY.MISSING"
    assert not (root / ".raptor/state/ingress.sqlite").exists()
    assert (root / ".raptor/state/ingress-report.json").is_file()


def test_missing_or_wrong_manifest_authorizes_no_scan(tmp_path: Path) -> None:
    root = _repository(tmp_path)

    with pytest.raises(ValueError, match="RAPTOR.PATH.OUTSIDE_ROOT"):
        configured_markdown_to_sqlite(
            root,
            ".raptor/missing.toml",
            ".raptor/state/ingress.sqlite",
            ".raptor/state/ingress-report.json",
        )
    with pytest.raises(ValueError, match="RAPTOR.CONFIG.MANIFEST"):
        configured_markdown_to_sqlite(
            root,
            ".raptor/sources.toml",
            ".raptor/state/ingress.sqlite",
            ".raptor/state/ingress-report.json",
        )


def test_invalid_overlapping_scan_config_authorizes_no_scan(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    (root / ".raptor/sources.toml").write_text(
        """schema_version = "1.0.0"

[[sources]]
name = "requirements"
root = "specifications"
include = ["**/*.md"]

[[sources]]
name = "nested"
root = "specifications/nested"
include = ["**/*.md"]
"""
    )

    with pytest.raises(ValueError, match="RAPTOR.CONFIG.VALIDATION"):
        configured_markdown_to_sqlite(
            root,
            ".raptor/raptor.toml",
            ".raptor/state/ingress.sqlite",
            ".raptor/state/ingress-report.json",
        )
    assert not (root / ".raptor/state/ingress.sqlite").exists()
    assert not (root / ".raptor/state/ingress-report.json").exists()
