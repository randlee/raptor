from __future__ import annotations

import json
import os
import shutil
import sqlite3
import stat
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError
from raptor_schema import (
    ReferenceValidationError,
    SourceDocument,
    dump_canonical_json,
    load_canonical_json,
)

from runtime.identity import document_identity, load_identity, register_identity
from runtime.cli import emit, failure, success
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
PLUGIN = REPO / "plugins/raptor"


def _repo(tmp_path: Path) -> tuple[Path, SourceDocument]:
    root = tmp_path / "consumer"
    (root / "docs").mkdir(parents=True)
    (root / "docs/requirements.md").write_text(
        """# Raptor-owned contract

### REQ-RAP-001 — Canonical artifact families
Define the canonical families.
Acceptance: all families validate.

### NFR-RAP-004 — Deterministic output
Canonical output is deterministic.
Acceptance: repeated output is identical.

### ADR-RAP-001 — Consumer-neutral contract
## Context
Consumers use different source formats.
## Decision
Use a canonical contract.
## Consequences
Profiles map source formats.

### DES-RAP-001 — Canonical model package
Overview: The package validates canonical documents.
Component: Canonical API | Validate and serialize source documents.
Dependencies: urn:raptor:repo:raptor/ADR-RAP-001
Interface: Source profile | Maps Markdown into canonical documents. | Consumer, Raptor

### TST-RAP-001 — Canonical verification
Objective: Prove all canonical families validate.
Scope: The consumer-neutral schema package.
Test Case: TC-RAP-001 | Validate all families | Load the document; Validate it | Validation succeeds.
Verifies: urn:raptor:repo:raptor/REQ-RAP-001,urn:raptor:repo:raptor/NFR-RAP-004
Exit Criteria: All validation succeeds.
"""
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
    with pytest.raises(ValueError, match="RAPTOR.IDENTITY.REUSE"):
        register_identity(
            root,
            repository_id="urn:raptor:repo:one",
            document_id="DOC-RAP-001",
            repository_path="docs/a.md",
            registered_repository_id="urn:raptor:repo:other",
            apply=True,
        )
    assert not (root / ".raptor/identity.json").exists()
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
    with pytest.raises(ValueError, match="RAPTOR.IDENTITY.REUSE"):
        register_identity(
            root,
            repository_id="urn:raptor:repo:one",
            document_id="DOC-RAP-001",
            repository_path="docs/a.md",
            registered_repository_id="urn:raptor:repo:other",
        )
    with pytest.raises(ValueError, match="RAPTOR.IDENTITY.MISSING") as missing:
        document_identity(root, "docs/missing.md")
    assert missing.value.suggested_action == (
        "python plugins/raptor/scripts/identity.py register --repo-root <repo-root> "
        "--repository-id urn:raptor:repo:one --document-id <document-id> "
        "--path docs/missing.md --apply"
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


def test_cli_preserves_identity_remediation_and_reference_diagnostic(
    tmp_path: Path,
) -> None:
    secret_repository = "urn:raptor:repo:secret-token-sk_live_1234567890"
    missing = tmp_path / "missing"
    (missing / "docs").mkdir(parents=True)
    (missing / "docs/source.md").write_text(
        "### REQ-RAP-001 — Requirement\nStatement.\nAcceptance: accepted.\n"
    )
    command = [
        sys.executable,
        str(PLUGIN / "scripts/validate.py"),
        "markdown",
        "--repo-root",
        str(missing),
        "--input",
        "docs/source.md",
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    envelope = json.loads(result.stdout.split("```json\n", 1)[1].rsplit("\n```", 1)[0])
    assert envelope["error"] == {
        "code": "RAPTOR.IDENTITY.MISSING",
        "message": "RAPTOR.IDENTITY.MISSING: explicit repository, document, and path registration is required",
        "recoverable": False,
        "suggested_action": "python plugins/raptor/scripts/identity.py register --repo-root <repo-root> --repository-id <repository-id> --document-id <document-id> --path docs/source.md --apply",
    }

    root, document = _repo(tmp_path)
    payload = document.model_dump(mode="json", exclude_none=True)
    payload["artifacts"][0]["relationships"] = [
        {
            "relation": "relates_to",
            "target": {
                "target_kind": "artifact",
                "repository_id": secret_repository,
                "artifact_id": "REQ-RAP-999",
            },
        }
    ]
    (root / "unresolved.json").write_text(
        dump_canonical_json(SourceDocument.model_validate(payload))
    )
    result = subprocess.run(
        [
            sys.executable,
            str(PLUGIN / "scripts/validate.py"),
            "json",
            "--repo-root",
            str(root),
            "--input",
            "unresolved.json",
            "--reference-mode",
            "document",
        ],
        capture_output=True,
        text=True,
    )
    envelope = json.loads(result.stdout.split("```json\n", 1)[1].rsplit("\n```", 1)[0])
    encoded_envelope = json.dumps(envelope)
    assert "SECRET_TOKEN" not in encoded_envelope and "sk_live_" not in encoded_envelope
    diagnostic = json.loads(envelope["error"]["message"])
    assert envelope["error"]["code"] == "RAPTOR.REFERENCE.UNRESOLVED"
    assert diagnostic["repository_id"] == "urn:raptor:repo:raptor"
    assert diagnostic["document_id"] == "DOC-RAP-001"
    assert diagnostic["repository_path"] == "docs/requirements.md"
    assert diagnostic["mode"] == "document"
    assert diagnostic["relation"] == "relates_to"
    assert diagnostic["source"] == {
        "repository_id": "urn:raptor:repo:raptor",
        "artifact_id": "REQ-RAP-001",
    }
    assert diagnostic["target"] == {
        "repository_id": "urn:raptor:repo:secret-token-[REDACTED]",
        "artifact_id": "REQ-RAP-999",
    }
    assert diagnostic["document_key"] == {
        "repository_id": "urn:raptor:repo:raptor",
        "document_id": "DOC-RAP-001",
    }
    assert diagnostic["json_pointer"] == "/artifacts/0/relationships/0/target"


def test_cli_redacts_untrusted_and_pydantic_error_values(
    capsys: pytest.CaptureFixture[str],
) -> None:
    secret = "SECRET_TOKEN_sk_live_1234567890"
    namespaced = failure(ValueError(f"RAPTOR.INPUT.INVALID: value={secret}"))
    encoded = json.dumps(namespaced)
    assert secret not in encoded and "sk_live_" not in encoded

    with pytest.raises(ValidationError) as caught:
        SourceDocument.model_validate({"schema_version": secret})
    pydantic = failure(caught.value)
    assert pydantic["error"] == {
        "code": "RAPTOR.VALIDATION.ERROR",
        "message": "RAPTOR.VALIDATION.ERROR: input failed schema validation",
        "recoverable": False,
        "suggested_action": "Correct the reported plugin state and retry.",
    }
    assert secret not in json.dumps(pydantic)
    emit(
        success(
            {
                "nested": [
                    {
                        "message": "Authorization: ApiKey abc123\nSafe: visible",
                        "digest": 'Authorization: Digest username="admin", realm="private", nonce="123"',
                        "dsn": "mysql://admin:database-secret@example.test/db",
                        "git": "git+ssh://token-only@example.test/repository",
                    }
                ]
            }
        )
    )
    emitted = capsys.readouterr().out
    assert "abc123" not in emitted
    assert "username" not in emitted and "nonce" not in emitted
    assert "database-secret" not in emitted
    assert "token-only" not in emitted
    assert "Safe: visible" in emitted


def test_repository_io_windows_branch_uses_handle_safe_contracts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from runtime import io as runtime_io

    observed: list[tuple[str, tuple[str, ...], bytes | None]] = []
    monkeypatch.setattr(runtime_io, "_is_windows", lambda: True)
    monkeypatch.setattr(
        runtime_io,
        "_windows_repository_read",
        lambda root, parts: observed.append(("read", parts, None)) or b"safe",
    )
    monkeypatch.setattr(
        runtime_io,
        "_windows_repository_publish",
        lambda root, parts, value: observed.append(("write", parts, value)),
    )
    assert runtime_io.read_repository_bytes(tmp_path, "docs/input.md") == b"safe"
    runtime_io.atomic_repository_bytes(tmp_path, "out/result.json", b"value")
    assert observed == [
        ("read", ("docs", "input.md"), None),
        ("write", ("out", "result.json"), b"value"),
    ]


def test_windows_repository_read_is_bound_to_verified_handle(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from runtime import io as runtime_io

    source = tmp_path / "docs"
    source.mkdir()
    (source / "source.json").write_bytes(b"verified")
    attacker = tmp_path / "attacker"
    attacker.mkdir()
    (attacker / "source.json").write_bytes(b"attacker")

    def open_root(path: Path, *, write: bool, directory: bool, create: bool) -> int:
        assert path == tmp_path and not write and directory and not create
        return runtime_io.os.open(path, runtime_io.os.O_RDONLY)

    def open_relative(
        parent: int, name: str, *, write: bool, directory: bool, create: bool
    ) -> int:
        descriptor = runtime_io.os.open(name, runtime_io.os.O_RDONLY, dir_fd=parent)
        if directory:
            source.rename(tmp_path / "retained-docs")
            source.symlink_to(attacker, target_is_directory=True)
        return descriptor

    monkeypatch.setattr(runtime_io, "_windows_open_checked", open_root)
    monkeypatch.setattr(runtime_io, "_windows_open_relative", open_relative)
    assert (
        runtime_io._windows_repository_read(tmp_path, ("docs", "source.json"))
        == b"verified"
    )
    assert (source / "source.json").read_bytes() == b"attacker"


def test_windows_repository_read_is_bound_to_verified_final_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from runtime import io as runtime_io

    source = tmp_path / "source.json"
    source.write_bytes(b"verified")

    def open_root(path: Path, *, write: bool, directory: bool, create: bool) -> int:
        return runtime_io.os.open(path, runtime_io.os.O_RDONLY)

    def open_relative(
        parent: int, name: str, *, write: bool, directory: bool, create: bool
    ) -> int:
        descriptor = runtime_io.os.open(name, runtime_io.os.O_RDONLY, dir_fd=parent)
        source.rename(tmp_path / "retained-source.json")
        source.write_bytes(b"attacker")
        return descriptor

    monkeypatch.setattr(runtime_io, "_windows_open_checked", open_root)
    monkeypatch.setattr(runtime_io, "_windows_open_relative", open_relative)
    assert (
        runtime_io._windows_repository_read(tmp_path, ("source.json",)) == b"verified"
    )
    assert source.read_bytes() == b"attacker"


def test_windows_repository_publish_renames_relative_to_verified_parent_handle(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from runtime import io as runtime_io

    output = tmp_path / "output"
    output.mkdir()
    attacker = tmp_path / "attacker-output"
    attacker.mkdir()
    opened_temporary: list[str] = []
    renamed: list[tuple[int, int, str]] = []

    def open_checked(path: Path, *, write: bool, directory: bool, create: bool) -> int:
        assert path == tmp_path and write and directory and not create
        return runtime_io.os.open(path, runtime_io.os.O_RDONLY)

    def open_relative(
        parent: int, name: str, *, write: bool, directory: bool, create: bool
    ) -> int:
        if directory:
            descriptor = runtime_io.os.open(name, runtime_io.os.O_RDONLY, dir_fd=parent)
            output.rename(tmp_path / "retained-output")
            output.symlink_to(attacker, target_is_directory=True)
            return descriptor
        assert write and create
        opened_temporary.append(name)
        return runtime_io.os.open(
            name,
            runtime_io.os.O_RDWR | runtime_io.os.O_CREAT | runtime_io.os.O_EXCL,
            dir_fd=parent,
        )

    def rename_relative(descriptor: int, parent: int, name: str) -> None:
        assert runtime_io.os.fstat(descriptor).st_size == len(b"published")
        assert stat.S_ISDIR(runtime_io.os.fstat(parent).st_mode)
        assert (
            runtime_io.os.fstat(parent).st_ino
            == (tmp_path / "retained-output").stat().st_ino
        )
        runtime_io.os.rename(
            opened_temporary[0], name, src_dir_fd=parent, dst_dir_fd=parent
        )
        renamed.append((descriptor, parent, name))

    monkeypatch.setattr(runtime_io, "_windows_open_checked", open_checked)
    monkeypatch.setattr(runtime_io, "_windows_open_relative", open_relative)
    monkeypatch.setattr(runtime_io, "_windows_rename_relative", rename_relative)
    runtime_io._windows_repository_publish(
        tmp_path, ("output", "result.json"), b"published"
    )
    assert len(opened_temporary) == 1
    assert renamed and renamed[0][2] == "result.json"
    assert (tmp_path / "retained-output/result.json").read_bytes() == b"published"
    assert not (attacker / "result.json").exists()


def test_windows_repository_publish_replaces_swapped_final_reparse_point(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from runtime import io as runtime_io

    output = tmp_path / "output"
    output.mkdir()
    destination = output / "result.json"
    destination.write_bytes(b"old")
    outside = tmp_path / "outside.json"
    outside.write_bytes(b"outside")
    temporary: list[str] = []

    def open_checked(path: Path, **options: object) -> int:
        return runtime_io.os.open(path, runtime_io.os.O_RDONLY)

    def open_relative(
        parent: int, name: str, *, write: bool, directory: bool, create: bool
    ) -> int:
        if directory:
            return runtime_io.os.open(name, runtime_io.os.O_RDONLY, dir_fd=parent)
        temporary.append(name)
        return runtime_io.os.open(
            name,
            runtime_io.os.O_RDWR | runtime_io.os.O_CREAT | runtime_io.os.O_EXCL,
            dir_fd=parent,
        )

    def swap_then_rename(descriptor: int, parent: int, name: str) -> None:
        destination.unlink()
        destination.symlink_to(outside)
        runtime_io.os.rename(temporary[0], name, src_dir_fd=parent, dst_dir_fd=parent)

    monkeypatch.setattr(runtime_io, "_windows_open_checked", open_checked)
    monkeypatch.setattr(runtime_io, "_windows_open_relative", open_relative)
    monkeypatch.setattr(runtime_io, "_windows_rename_relative", swap_then_rename)
    runtime_io._windows_repository_publish(
        tmp_path, ("output", "result.json"), b"published"
    )
    assert destination.read_bytes() == b"published" and not destination.is_symlink()
    assert outside.read_bytes() == b"outside"


@pytest.mark.skipif(os.name != "nt", reason="native Windows repository I/O")
def test_windows_repository_io_native_round_trip(tmp_path: Path) -> None:
    from runtime import io as runtime_io

    runtime_io.atomic_repository_bytes(tmp_path, "nested/result.json", b"native")
    outside = tmp_path / "outside.json"
    outside.write_bytes(b"outside")
    destination = tmp_path / "nested/result.json"
    destination.unlink()
    try:
        destination.symlink_to(outside)
    except OSError:
        pytest.skip("Windows host cannot create a file reparse point")
    runtime_io.atomic_repository_bytes(tmp_path, "nested/result.json", b"replacement")
    assert (
        runtime_io.read_repository_bytes(tmp_path, "nested/result.json")
        == b"replacement"
    )
    assert not destination.is_symlink() and outside.read_bytes() == b"outside"


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


def test_markdown_directory_defaults_to_batch_and_rejects_empty_or_wrong_mode(
    tmp_path: Path,
) -> None:
    root = tmp_path / "consumer"
    source = root / "docs"
    source.mkdir(parents=True)

    def body(plan_id: str, case_id: str, target: str) -> str:
        return f"""### {plan_id} — Batch plan
Objective: Validate a cyclic batch.
Scope: The two source documents.
Test Case: {case_id} | Validate peer | Load peer; Validate peer | Peer validates.
Verifies: urn:raptor:repo:batch/{target}
Exit Criteria: Both peers validate.
"""

    (source / "a.md").write_text(body("TST-RAP-010", "TC-RAP-010", "TST-RAP-011"))
    (source / "b.md").write_text(body("TST-RAP-011", "TC-RAP-011", "TST-RAP-010"))
    for document_id, path in (
        ("DOC-RAP-010", "docs/a.md"),
        ("DOC-RAP-011", "docs/b.md"),
    ):
        register_identity(
            root,
            repository_id="urn:raptor:repo:batch",
            document_id=document_id,
            repository_path=path,
            apply=True,
        )
    result = markdown_to_json(root, "docs", "generated", apply=True)
    assert result["outputs"] == [
        "generated/DOC-RAP-010.json",
        "generated/DOC-RAP-011.json",
    ]
    with pytest.raises(ValueError, match="RAPTOR.REFERENCE.MODE_MISMATCH"):
        markdown_to_json(root, "docs", "generated", reference_mode="document")
    for mode in ("structural", "store"):
        with pytest.raises(ValueError, match="RAPTOR.REFERENCE.MODE_MISMATCH"):
            validate_markdown(root, "docs", reference_mode=mode)
    for mode in ("structural", "batch", "store"):
        with pytest.raises(ValueError, match="RAPTOR.REFERENCE.MODE_MISMATCH"):
            validate_markdown(root, "docs/a.md", reference_mode=mode)
    (root / "empty").mkdir()
    with pytest.raises(ValueError, match="RAPTOR.OPERATION.EMPTY_INPUT"):
        validate_markdown(root, "empty")
    single = root / "single"
    single.mkdir()
    (single / "only.md").write_text(
        "### REQ-RAP-020 — Single document\nStatement.\nAcceptance: accepted.\n"
    )
    register_identity(
        root,
        repository_id="urn:raptor:repo:batch",
        document_id="DOC-RAP-020",
        repository_path="single/only.md",
        apply=True,
    )
    assert validate_markdown(root, "single")["documents"][0]["document_id"] == (
        "DOC-RAP-020"
    )
    with pytest.raises(ValueError, match="RAPTOR.REFERENCE.MODE_MISMATCH"):
        validate_markdown(root, "single", reference_mode="document")


def test_failures_do_not_mutate_output_database_or_escape_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
    monkeypatch.setattr(
        "runtime.operations.atomic_repository_bytes",
        lambda *args: (_ for _ in ()).throw(OSError("publish fault")),
    )
    with pytest.raises(OSError, match="publish fault"):
        import_sqlite(root, "canonical.json", "raptor.sqlite", apply=True)
    assert (root / "raptor.sqlite").read_bytes() == before
    with pytest.raises(OSError, match="publish fault"):
        import_sqlite(root, "canonical.json", "fresh.sqlite", apply=True)
    assert not (root / "fresh.sqlite").exists()
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


def test_operation_paths_reject_symlink_components(tmp_path: Path) -> None:
    root, _ = _repo(tmp_path)
    (root / "alias.json").symlink_to("canonical.json")
    with pytest.raises(ValueError, match="RAPTOR.PATH.OUTSIDE_ROOT"):
        validate_json(root, "alias.json")
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "linked").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="RAPTOR.PATH.OUTSIDE_ROOT"):
        markdown_to_json(root, "docs/requirements.md", "linked/output.json", apply=True)
    import_sqlite(root, "canonical.json", "raptor.sqlite", apply=True)
    (root / "store-link.sqlite").symlink_to("raptor.sqlite")
    with pytest.raises(ValueError, match="RAPTOR.PATH.OUTSIDE_ROOT"):
        validate_sqlite(root, "store-link.sqlite")


def test_read_only_validation_refuses_journal_recovery(tmp_path: Path) -> None:
    root, _ = _repo(tmp_path)
    import_sqlite(root, "canonical.json", "raptor.sqlite", apply=True)
    sidecar = root / "raptor.sqlite-wal"
    sidecar.write_bytes(b"untrusted pending state")
    before = (root / "raptor.sqlite").read_bytes(), sidecar.read_bytes()
    with pytest.raises(ValueError, match="RAPTOR.STORAGE.READ_ONLY_SIDECAR"):
        validate_sqlite(root, "raptor.sqlite")
    assert ((root / "raptor.sqlite").read_bytes(), sidecar.read_bytes()) == before
