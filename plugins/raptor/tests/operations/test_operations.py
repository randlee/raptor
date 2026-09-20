from __future__ import annotations

import json
import shutil
import sqlite3
import stat
import subprocess
import sys
from pathlib import Path

import pytest
from raptor_schema import (
    ReferenceValidationError,
    SourceDocument,
    dump_canonical_json,
    load_canonical_json,
)

from runtime.identity import load_identity, register_identity
from runtime.operations import (
    export_sqlite,
    import_sqlite,
    markdown_to_json,
    repository_path,
    validate_json,
    validate_markdown,
    validate_sqlite,
)

REPO = Path(__file__).parents[4]
CORPUS = REPO / "schema/tests/corpus/all-families.json"
PLUGIN = REPO / "plugins/raptor"


def _repo(tmp_path: Path) -> tuple[Path, SourceDocument]:
    root = tmp_path / "consumer"
    (root / "docs").mkdir(parents=True)
    original = load_canonical_json(CORPUS.read_bytes())
    body = json.dumps(
        [item.model_dump(mode="json", exclude_none=True) for item in original.artifacts]
    )
    (root / "docs/requirements.md").write_text(
        f"# Raptor-owned contract\n\n```raptor-json\n{body}\n```\n"
    )
    register_identity(
        root,
        repository_id="urn:raptor:repo:raptor",
        document_id="DOC-RAP-001",
        repository_path="docs/requirements.md",
        apply=True,
    )
    markdown_to_json(root, "docs/requirements.md", "canonical.json", apply=True)
    return root, load_canonical_json((root / "canonical.json").read_bytes())


def test_identity_validate_apply_repeat_clone_and_conflicts(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    result = register_identity(
        root,
        repository_id="urn:raptor:repo:one",
        document_id="DOC-RAP-001",
        repository_path="docs/a.md",
    )
    assert result["changed"] is True and not (root / ".raptor/identity.json").exists()
    register_identity(
        root,
        repository_id="urn:raptor:repo:one",
        document_id="DOC-RAP-001",
        repository_path="docs/a.md",
        apply=True,
    )
    before = (root / ".raptor/identity.json").read_bytes()
    assert (
        register_identity(
            root,
            repository_id="urn:raptor:repo:one",
            document_id="DOC-RAP-001",
            repository_path="docs/a.md",
            apply=True,
        )["changed"]
        is False
    )
    clone = tmp_path / "clone"
    shutil.copytree(root, clone)
    assert load_identity(clone) == load_identity(root)
    for repository_id, document_id, path, code in (
        ("urn:raptor:repo:two", "DOC-RAP-001", "docs/a.md", "REPOSITORY_CONFLICT"),
        ("urn:raptor:repo:one", "DOC-RAP-001", "docs/b.md", "DOCUMENT_CONFLICT"),
        ("urn:raptor:repo:one", "DOC-RAP-002", "docs/a.md", "PATH_CONFLICT"),
    ):
        with pytest.raises(ValueError, match=code):
            register_identity(
                root,
                repository_id=repository_id,
                document_id=document_id,
                repository_path=path,
            )
    assert (root / ".raptor/identity.json").read_bytes() == before


def test_identity_cli_validate_apply_and_conflict_envelopes(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    base = [
        sys.executable,
        str(PLUGIN / "scripts/identity.py"),
        "register",
        "--repo-root",
        str(root),
        "--repository-id",
        "urn:raptor:repo:one",
        "--document-id",
        "DOC-RAP-001",
        "--path",
        "docs/a.md",
    ]
    validate = subprocess.run(base + ["--validate"], capture_output=True, text=True)
    assert validate.returncode == 0 and not (root / ".raptor/identity.json").exists()
    apply = subprocess.run(base + ["--apply"], capture_output=True, text=True)
    assert apply.returncode == 0 and (root / ".raptor/identity.json").is_file()
    conflict = subprocess.run(
        [value if value != "docs/a.md" else "docs/b.md" for value in base]
        + ["--validate"],
        capture_output=True,
        text=True,
    )
    assert conflict.returncode == 1
    payload = json.loads(conflict.stdout.split("```json\n", 1)[1].rsplit("\n```", 1)[0])
    assert payload["error"]["code"] == "RAPTOR.IDENTITY.DOCUMENT_CONFLICT"


def test_markdown_json_sqlite_round_trip_and_validation_is_read_only(
    tmp_path: Path,
) -> None:
    root, document = _repo(tmp_path)
    assert {item.artifact_type for item in document.artifacts} == {
        "requirement",
        "non_functional_requirement",
        "architecture_decision",
        "design_document",
        "test_plan",
    }
    assert document.provenance.origin.repository_id == "urn:raptor:repo:raptor"
    assert document.provenance.origin == document.provenance.origin.model_copy()
    canonical_before = (root / "canonical.json").read_bytes()
    stat_before = (root / "canonical.json").stat()
    validate_markdown(root, "docs/requirements.md")
    validate_json(root, "canonical.json")
    markdown_to_json(root, "docs/requirements.md", "unused.json")
    assert not (root / "unused.json").exists()
    assert (root / "canonical.json").read_bytes() == canonical_before
    assert (root / "canonical.json").stat().st_mtime_ns == stat_before.st_mtime_ns
    assert stat.S_IMODE((root / "canonical.json").stat().st_mode) == stat.S_IMODE(
        stat_before.st_mode
    )

    import_sqlite(root, "canonical.json", "raptor.sqlite")
    assert not (root / "raptor.sqlite").exists()
    import_sqlite(root, "canonical.json", "raptor.sqlite", apply=True)
    database_before = (root / "raptor.sqlite").read_bytes()
    database_stat = (root / "raptor.sqlite").stat()
    validate_sqlite(root, "raptor.sqlite")
    export_sqlite(
        root, "raptor.sqlite", "urn:raptor:repo:raptor", "DOC-RAP-001", "export.json"
    )
    assert not (root / "export.json").exists()
    assert (root / "raptor.sqlite").read_bytes() == database_before
    assert (root / "raptor.sqlite").stat().st_mtime_ns == database_stat.st_mtime_ns
    assert stat.S_IMODE((root / "raptor.sqlite").stat().st_mode) == stat.S_IMODE(
        database_stat.st_mode
    )
    export_sqlite(
        root,
        "raptor.sqlite",
        "urn:raptor:repo:raptor",
        "DOC-RAP-001",
        "export.json",
        apply=True,
    )
    recovered = load_canonical_json((root / "export.json").read_bytes())
    assert recovered == document
    assert recovered.provenance.origin == document.provenance.origin


def test_reference_modes_cycles_store_and_cross_repository_failure(
    tmp_path: Path,
) -> None:
    root, document = _repo(tmp_path)
    payload = document.model_dump(mode="json", exclude_none=True)
    payload["artifacts"][0]["relationships"] = [
        {
            "relation": "relates_to",
            "target": {
                "target_kind": "artifact",
                "repository_id": "urn:raptor:repo:other",
                "artifact_id": "REQ-RAP-999",
            },
        }
    ]
    unresolved = SourceDocument.model_validate(payload)
    (root / "unresolved.json").write_text(dump_canonical_json(unresolved))
    validate_json(root, "unresolved.json", reference_mode="structural")
    with pytest.raises(
        ReferenceValidationError, match="RAPTOR.REFERENCE.UNRESOLVED"
    ) as caught:
        validate_json(root, "unresolved.json", reference_mode="document")
    error = caught.value
    assert error.mode.value == "document"
    assert (error.document_key.repository_id, error.document_key.document_id) == (
        "urn:raptor:repo:raptor",
        "DOC-RAP-001",
    )
    assert error.source.sort_key() == ("urn:raptor:repo:raptor", "REQ-RAP-001")
    assert error.target.sort_key() == ("urn:raptor:repo:other", "REQ-RAP-999")
    assert error.repository_path == "docs/requirements.md"
    assert error.json_pointer == "/artifacts/0/relationships/0/target"

    target_payload = document.model_dump(mode="json", exclude_none=True)
    target_payload["provenance"]["origin"].update(
        repository_id="urn:raptor:repo:other",
        document_id="DOC-RAP-999",
        initial_repository_path="docs/other.md",
    )
    target_payload["provenance"]["materialization"].update(
        repository_path="docs/other.md"
    )
    target_payload["artifacts"] = [
        {**target_payload["artifacts"][0], "id": "REQ-RAP-999", "relationships": []}
    ]
    target = SourceDocument.model_validate(target_payload)
    (root / "target.json").write_text(dump_canonical_json(target))
    import_sqlite(root, "target.json", "store.sqlite", apply=True)
    validate_json(
        root, "unresolved.json", reference_mode="store", database="store.sqlite"
    )

    # A two-document cycle is valid in batch mode and invalid per-document.
    left = payload
    left["provenance"]["origin"].update(
        document_id="DOC-RAP-010", initial_repository_path="docs/left.md"
    )
    left["provenance"]["materialization"].update(repository_path="docs/left.md")
    left["artifacts"] = [
        {
            **left["artifacts"][0],
            "id": "REQ-RAP-010",
            "relationships": [
                {
                    "relation": "relates_to",
                    "target": {
                        "target_kind": "artifact",
                        "repository_id": "urn:raptor:repo:raptor",
                        "artifact_id": "REQ-RAP-011",
                    },
                }
            ],
        }
    ]
    right = json.loads(json.dumps(left))
    right["provenance"]["origin"].update(
        document_id="DOC-RAP-011", initial_repository_path="docs/right.md"
    )
    right["provenance"]["materialization"].update(repository_path="docs/right.md")
    right["artifacts"][0].update(
        id="REQ-RAP-011",
        relationships=[
            {
                "relation": "relates_to",
                "target": {
                    "target_kind": "artifact",
                    "repository_id": "urn:raptor:repo:raptor",
                    "artifact_id": "REQ-RAP-010",
                },
            }
        ],
    )
    directory = root / "batch"
    directory.mkdir()
    (directory / "left.json").write_text(
        dump_canonical_json(SourceDocument.model_validate(left))
    )
    (directory / "right.json").write_text(
        dump_canonical_json(SourceDocument.model_validate(right))
    )
    validate_json(root, "batch", reference_mode="batch")
    import_sqlite(root, "batch", "cycle.sqlite", apply=True)
    validate_sqlite(root, "cycle.sqlite")


def test_failures_do_not_mutate_output_database_or_escape_root(tmp_path: Path) -> None:
    root, _ = _repo(tmp_path)
    import_sqlite(root, "canonical.json", "raptor.sqlite", apply=True)
    before = (root / "raptor.sqlite").read_bytes()
    (root / "bad.json").write_text("{}")
    with pytest.raises(ValueError):
        import_sqlite(root, "bad.json", "raptor.sqlite", apply=True)
    assert (root / "raptor.sqlite").read_bytes() == before
    document = load_canonical_json((root / "canonical.json").read_bytes())
    changed = document.model_dump(mode="json", exclude_none=True)
    changed["artifacts"][0]["title"] = "Semantic change without provenance transition"
    (root / "changed.json").write_text(
        dump_canonical_json(SourceDocument.model_validate(changed))
    )
    with pytest.raises(ValueError, match="RAPTOR.STORAGE.PROVENANCE_TRANSITION"):
        import_sqlite(root, "changed.json", "raptor.sqlite", apply=True)
    assert (root / "raptor.sqlite").read_bytes() == before
    for value in ("../outside", "/tmp/outside", "bad\\path"):
        with pytest.raises(ValueError, match="RAPTOR.PATH.OUTSIDE_ROOT"):
            repository_path(root, value)


def test_storage_corruption_is_deterministic_and_non_mutating(tmp_path: Path) -> None:
    root, _ = _repo(tmp_path)
    import_sqlite(root, "canonical.json", "raptor.sqlite", apply=True)
    connection = sqlite3.connect(root / "raptor.sqlite")
    connection.execute("UPDATE source_documents SET canonical_sha256 = ?", ("0" * 64,))
    connection.commit()
    connection.close()
    before = (root / "raptor.sqlite").read_bytes()
    with pytest.raises(ValueError, match="RAPTOR.STORAGE"):
        validate_sqlite(root, "raptor.sqlite")
    assert (root / "raptor.sqlite").read_bytes() == before
