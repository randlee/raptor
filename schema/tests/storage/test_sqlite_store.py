from __future__ import annotations

import hashlib
import json
import sqlite3
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from raptor_schema import (
    ArtifactKey,
    DocumentKey,
    ReferenceValidationError,
    SQLiteArtifactStore,
    SourceDocument,
    StorageError,
    assert_store_conformance,
    dump_canonical_json,
)

ROOT = Path(__file__).parents[3]
DDL = ROOT / "schema/sql/sqlite/0001_initial.sql"


def key(document: SourceDocument) -> DocumentKey:
    origin = document.provenance.origin
    return DocumentKey(
        repository_id=origin.repository_id, document_id=origin.document_id
    )


def make_document(
    *,
    repository_id: str = "urn:raptor:repo:alpha",
    document_id: str = "DOC-ALPHA-001",
    path: str = "docs/alpha.md",
    artifact_ids: tuple[str, ...] = ("REQ-ALPHA-001",),
    targets: tuple[tuple[str, str], ...] = (),
) -> SourceDocument:
    content_hash = hashlib.sha256(document_id.encode()).hexdigest()
    artifacts: list[dict[str, object]] = []
    for index, artifact_id in enumerate(artifact_ids):
        relationships = []
        if index < len(targets):
            target_repository, target_artifact = targets[index]
            relationships.append(
                {
                    "relation": "depends_on",
                    "target": {
                        "target_kind": "artifact",
                        "repository_id": target_repository,
                        "artifact_id": target_artifact,
                    },
                }
            )
        artifacts.append(
            {
                "artifact_type": "requirement",
                "id": artifact_id,
                "title": artifact_id,
                "status": "accepted",
                "relationships": relationships,
                "extensions": {},
                "statement": f"Store {artifact_id}.",
                "acceptance_criteria": ["It round-trips."],
            }
        )
    return SourceDocument.model_validate(
        {
            "schema_version": "1.0.0",
            "provenance": {
                "origin": {
                    "repository_id": repository_id,
                    "document_id": document_id,
                    "initial_repository_path": path,
                    "original_content_sha256": content_hash,
                    "source_format": "markdown",
                    "parser_profile": "raptor_test",
                    "parser_profile_version": "1.0.0",
                },
                "materialization": {
                    "repository_path": path,
                    "content_sha256": content_hash,
                    "operation": "imported",
                    "parser_profile": "raptor_test",
                    "parser_profile_version": "1.0.0",
                },
            },
            "artifacts": artifacts,
        }
    )


def other_repository(document_dict: dict[str, object]) -> SourceDocument:
    value = deepcopy(document_dict)
    old = "urn:raptor:repo:raptor"
    new = "urn:raptor:repo:other"
    value["provenance"]["origin"]["repository_id"] = new  # type: ignore[index]
    for artifact in value["artifacts"]:  # type: ignore[union-attr]
        for relationship in artifact.get("relationships", []):  # type: ignore[union-attr]
            target = relationship["target"]
            if target.get("repository_id") == old:
                target["repository_id"] = new
        for component in artifact.get("components", []):  # type: ignore[union-attr]
            for dependency in component["dependencies"]:
                if dependency["repository_id"] == old:
                    dependency["repository_id"] = new
        for test_case in artifact.get("test_cases", []):  # type: ignore[union-attr]
            for verified in test_case["verifies"]:
                if verified["repository_id"] == old:
                    verified["repository_id"] = new
    return SourceDocument.model_validate(value)


def test_conformance_and_exact_five_family_round_trip(
    document: SourceDocument,
) -> None:
    store = SQLiteArtifactStore()
    assert_store_conformance(store, [document])
    recovered = store.get_document(key(document))
    assert dump_canonical_json(recovered) == dump_canonical_json(document)
    assert len(recovered.artifacts) == 5


def test_initialize_in_memory_file_backed_and_idempotent(tmp_path: Path) -> None:
    memory = SQLiteArtifactStore()
    memory.initialize()
    memory.initialize()
    path = tmp_path / "raptor.db"
    file_store = SQLiteArtifactStore(path)
    file_store.initialize()
    assert path.is_file()
    assert file_store._connection.execute("PRAGMA foreign_keys").fetchone() == (1,)
    assert file_store._connection.execute(
        "SELECT count(*) FROM schema_metadata"
    ).fetchone() == (2,)


def test_schema_version_conflict_is_rejected() -> None:
    connection = sqlite3.connect(":memory:")
    store = SQLiteArtifactStore(connection)
    store.initialize()
    connection.execute(
        "UPDATE schema_metadata SET metadata_value = '999' WHERE metadata_key = 'database_schema_version'"
    )
    connection.commit()
    with pytest.raises(StorageError, match="SCHEMA_VERSION"):
        store.initialize()


def test_multi_repository_composite_keys_and_filtered_listing(
    document: SourceDocument, document_dict: dict[str, object]
) -> None:
    other = other_repository(document_dict)
    store = SQLiteArtifactStore()
    store.initialize()
    store.put_documents((document, other))
    assert store.get_document(key(document)).provenance.origin.repository_id != store.get_document(
        key(other)
    ).provenance.origin.repository_id
    assert len(store.list_artifact_keys()) == 10
    assert len(
        store.list_artifact_keys(
            repository_id="urn:raptor:repo:other", artifact_type="requirement"
        )
    ) == 1


def test_idempotent_retry_and_replacement(document: SourceDocument) -> None:
    store = SQLiteArtifactStore()
    store.initialize()
    store.put_document(document)
    store.put_document(document)
    assert len(store.list_artifact_keys()) == 5

    replacement = document.model_copy(deep=True)
    replacement.artifacts[0].title = "Updated requirement"
    replacement.artifacts.pop()
    store.put_document(replacement)
    recovered = store.get_document(key(document))
    assert recovered.artifacts[0].title == "Updated requirement"
    assert len(recovered.artifacts) == 4
    assert not store.contains(
        ArtifactKey(repository_id="urn:raptor:repo:raptor", artifact_id="TST-RAP-001")
    )


def test_atomic_rollback_on_path_collision() -> None:
    first = make_document()
    second = make_document(
        document_id="DOC-ALPHA-002",
        path="docs/alpha.md",
        artifact_ids=("REQ-ALPHA-002",),
    )
    store = SQLiteArtifactStore()
    store.initialize()
    with pytest.raises(sqlite3.IntegrityError):
        store.put_documents((first, second))
    assert store.list_artifact_keys() == []
    with pytest.raises(KeyError):
        store.get_document(key(first))


def test_foreign_keys_are_enabled_and_ddl_is_authoritative() -> None:
    connection = sqlite3.connect(":memory:")
    store = SQLiteArtifactStore(connection)
    store.initialize()
    assert connection.execute("PRAGMA foreign_keys").fetchone() == (1,)
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO artifacts VALUES (?, ?, ?, ?, ?)",
            ("urn:raptor:repo:missing", "REQ-X-001", "requirement", "draft", "{}"),
        )
    ddl = DDL.read_text(encoding="utf-8")
    for table in (
        "schema_metadata",
        "repositories",
        "source_documents",
        "artifacts",
        "document_artifacts",
        "artifact_relationships",
        "artifact_uri_relationships",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in ddl
    assert "CHECK (json_valid(" in ddl
    assert "FOREIGN KEY" in ddl and "UNIQUE" in ddl
    assert "('database_schema_version', '1')" in ddl
    assert "('canonical_model_schema_version', '1.0.0')" in ddl


@pytest.mark.parametrize(
    ("sql", "parameters"),
    [
        (
            "UPDATE artifacts SET status = 'rejected' WHERE repository_id = ? AND artifact_id = ?",
            ("urn:raptor:repo:raptor", "REQ-RAP-001"),
        ),
        (
            "UPDATE document_artifacts SET ordinal = 10 WHERE repository_id = ? AND artifact_id = ?",
            ("urn:raptor:repo:raptor", "TST-RAP-001"),
        ),
        (
            "DELETE FROM artifact_relationships WHERE source_repository_id = ? AND source_artifact_id = ?",
            ("urn:raptor:repo:raptor", "NFR-RAP-004"),
        ),
    ],
    ids=["scalar", "membership", "relationship"],
)
def test_projection_corruption_is_detected(
    document: SourceDocument, sql: str, parameters: tuple[str, str]
) -> None:
    connection = sqlite3.connect(":memory:")
    store = SQLiteArtifactStore(connection)
    store.initialize()
    store.put_document(document)
    connection.execute(sql, parameters)
    connection.commit()
    with pytest.raises(StorageError, match="PROJECTION_MISMATCH"):
        store.get_document(key(document))


def test_delete_and_inbound_reference_restriction() -> None:
    target = make_document()
    source = make_document(
        repository_id="urn:raptor:repo:beta",
        document_id="DOC-BETA-001",
        path="docs/beta.md",
        artifact_ids=("REQ-BETA-001",),
        targets=(("urn:raptor:repo:alpha", "REQ-ALPHA-001"),),
    )
    store = SQLiteArtifactStore()
    store.initialize()
    store.put_documents((target, source))
    with pytest.raises(StorageError, match="REFERENCE_CONFLICT"):
        store.delete_document(key(target))
    store.delete_document(key(source))
    store.delete_document(key(target))
    assert store.list_artifact_keys() == []


def test_replacement_cannot_remove_externally_referenced_artifact() -> None:
    target = make_document(
        artifact_ids=("REQ-ALPHA-001", "REQ-ALPHA-002")
    )
    source = make_document(
        repository_id="urn:raptor:repo:beta",
        document_id="DOC-BETA-001",
        path="docs/beta.md",
        artifact_ids=("REQ-BETA-001",),
        targets=(("urn:raptor:repo:alpha", "REQ-ALPHA-002"),),
    )
    store = SQLiteArtifactStore()
    store.initialize()
    store.put_documents((target, source))
    replacement = target.model_copy(deep=True)
    replacement.artifacts.pop()
    with pytest.raises(StorageError, match="REFERENCE_CONFLICT"):
        store.put_document(replacement)
    assert len(store.get_document(key(target)).artifacts) == 2


def test_rendered_path_update_and_invalid_transition(document: SourceDocument) -> None:
    store = SQLiteArtifactStore()
    store.initialize()
    store.put_document(document)
    old_materialization = document.provenance.materialization
    imported_rewrite = document.model_copy(
        deep=True,
        update={
            "provenance": document.provenance.model_copy(
                update={
                    "materialization": old_materialization.model_copy(
                        update={"parser_profile": "other_profile"}
                    )
                }
            )
        },
    )
    with pytest.raises(StorageError, match="PROVENANCE_TRANSITION"):
        store.put_document(imported_rewrite)

    rendered = document.model_copy(deep=True)
    rendered.provenance.materialization = old_materialization.model_copy(
        update={
            "repository_path": "generated/requirements.md",
            "content_sha256": "b" * 64,
            "operation": "rendered",
            "parent_content_sha256": old_materialization.content_sha256,
            "template_set": "raptor_markdown",
            "template_version": "1.0.0",
        }
    )
    store.put_document(rendered)
    assert (
        store.get_document(key(document)).provenance.materialization.repository_path
        == "generated/requirements.md"
    )

    invalid = rendered.model_copy(deep=True)
    invalid.provenance.materialization = rendered.provenance.materialization.model_copy(
        update={"repository_path": "generated/other.md", "parent_content_sha256": "c" * 64}
    )
    with pytest.raises(StorageError, match="PROVENANCE_TRANSITION"):
        store.put_document(invalid)


def test_origin_rewrite_is_rejected(document: SourceDocument) -> None:
    store = SQLiteArtifactStore()
    store.initialize()
    store.put_document(document)
    rewritten_provenance = document.provenance.model_copy(
        update={
            "origin": document.provenance.origin.model_copy(
                update={"original_content_sha256": "c" * 64}
            ),
            "materialization": document.provenance.materialization.model_copy(
                update={"content_sha256": "c" * 64}
            ),
        }
    )
    rewritten = document.model_copy(
        deep=True,
        update={"provenance": rewritten_provenance},
    )
    with pytest.raises(StorageError, match="PROVENANCE_TRANSITION"):
        store.put_document(rewritten)


def test_reference_modes_staged_cycle_existing_store_and_missing_rollback() -> None:
    first = make_document(
        artifact_ids=("REQ-ALPHA-001",),
        targets=(("urn:raptor:repo:beta", "REQ-BETA-001"),),
    )
    second = make_document(
        repository_id="urn:raptor:repo:beta",
        document_id="DOC-BETA-001",
        path="docs/beta.md",
        artifact_ids=("REQ-BETA-001",),
        targets=(("urn:raptor:repo:alpha", "REQ-ALPHA-001"),),
    )
    store = SQLiteArtifactStore()
    store.initialize()
    store.put_documents((first, second))
    assert len(store.list_artifact_keys()) == 2

    existing_target = make_document(
        repository_id="urn:raptor:repo:target",
        document_id="DOC-TARGET-001",
        path="docs/target.md",
        artifact_ids=("REQ-TARGET-001",),
    )
    store.put_document(existing_target)
    existing_source = make_document(
        repository_id="urn:raptor:repo:source",
        document_id="DOC-SOURCE-001",
        path="docs/source.md",
        artifact_ids=("REQ-SOURCE-001",),
        targets=(("urn:raptor:repo:target", "REQ-TARGET-001"),),
    )
    store.put_document(existing_source)

    missing = make_document(
        repository_id="urn:raptor:repo:missing-source",
        document_id="DOC-MISSING-001",
        path="docs/missing.md",
        artifact_ids=("REQ-MISSING-001",),
        targets=(("urn:raptor:repo:absent", "REQ-ABSENT-001"),),
    )
    valid = make_document(
        repository_id="urn:raptor:repo:valid",
        document_id="DOC-VALID-001",
        path="docs/valid.md",
        artifact_ids=("REQ-VALID-001",),
    )
    with pytest.raises(ReferenceValidationError, match="REFERENCE.UNRESOLVED"):
        store.put_documents((valid, missing))
    assert not store.contains(
        ArtifactKey(repository_id="urn:raptor:repo:valid", artifact_id="REQ-VALID-001")
    )


def test_invalid_model_never_reaches_storage(document_dict: dict[str, object]) -> None:
    document_dict["artifacts"][0]["id"] = "NFR-RAP-001"  # type: ignore[index]
    with pytest.raises(ValidationError):
        SourceDocument.model_validate(document_dict)
