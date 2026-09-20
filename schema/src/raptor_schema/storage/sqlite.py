from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import cast

from pydantic import BaseModel

from ..canonical import (
    ReferenceValidationMode,
    dump_canonical_json,
    validate_document,
    validate_documents,
)
from ..models import (
    ArtifactKey,
    ArtifactTarget,
    DesignDocument,
    DocumentKey,
    RepositoryId,
    SourceDocument,
    TestPlan,
    UriTarget,
    validate_provenance_transition,
)

DATABASE_SCHEMA_VERSION = "1"
MODEL_SCHEMA_VERSION = "1.0.0"
_METADATA = {
    "database_schema_version": DATABASE_SCHEMA_VERSION,
    "canonical_model_schema_version": MODEL_SCHEMA_VERSION,
}


class StorageError(ValueError):
    pass


def _json(model: BaseModel) -> str:
    return json.dumps(
        model.model_dump(mode="json", exclude_none=True),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _document_key(document: SourceDocument) -> DocumentKey:
    origin = document.provenance.origin
    return DocumentKey(
        repository_id=origin.repository_id, document_id=origin.document_id
    )


def _artifact_keys(document: SourceDocument) -> set[tuple[str, str]]:
    repository_id = document.provenance.origin.repository_id
    return {(repository_id, artifact.id) for artifact in document.artifacts}


def _relationship_rows(
    document: SourceDocument,
) -> tuple[
    set[tuple[str, str, str, str, str, str | None]],
    set[tuple[str, str, str, str, str | None]],
]:
    repository_id = document.provenance.origin.repository_id
    typed_by_key: dict[tuple[str, str, str, str, str], str | None] = {}
    uris: set[tuple[str, str, str, str, str | None]] = set()
    for artifact in document.artifacts:
        for relationship in artifact.relationships:
            target = relationship.target
            if isinstance(target, ArtifactTarget):
                typed_by_key[
                    (
                        repository_id,
                        artifact.id,
                        relationship.relation.value,
                        target.repository_id,
                        target.artifact_id,
                    )
                ] = relationship.description
            elif isinstance(target, UriTarget):
                uris.add(
                    (
                        repository_id,
                        artifact.id,
                        relationship.relation.value,
                        target.target_uri,
                        relationship.description,
                    )
                )
        if isinstance(artifact, DesignDocument):
            for component in artifact.components:
                for dependency in component.dependencies:
                    typed_by_key.setdefault(
                        (
                            repository_id,
                            artifact.id,
                            "depends_on",
                            dependency.repository_id,
                            dependency.artifact_id,
                        ),
                        None,
                    )
        if isinstance(artifact, TestPlan):
            for test_case in artifact.test_cases:
                for verified in test_case.verifies:
                    typed_by_key.setdefault(
                        (
                            repository_id,
                            artifact.id,
                            "verifies",
                            verified.repository_id,
                            verified.artifact_id,
                        ),
                        None,
                    )
    typed = {(*key, description) for key, description in typed_by_key.items()}
    return typed, uris


class _OverlayResolver:
    def __init__(
        self,
        store: "SQLiteArtifactStore",
        staged: set[tuple[str, str]],
        replaced_documents: set[tuple[str, str]],
    ) -> None:
        self._store = store
        self._staged = staged
        self._replaced_documents = replaced_documents

    def contains(self, key: ArtifactKey) -> bool:
        value = key.sort_key()
        if value in self._staged:
            return True
        owner = self._store._artifact_owner(value)
        return owner is not None and owner not in self._replaced_documents


class SQLiteArtifactStore:
    def __init__(
        self,
        database: str | Path | sqlite3.Connection = ":memory:",
        *,
        ddl_path: Path | None = None,
    ) -> None:
        if isinstance(database, sqlite3.Connection):
            self._connection = database
            self._owns_connection = False
        else:
            self._connection = sqlite3.connect(str(database), isolation_level=None)
            self._owns_connection = True
        self._ddl_path = ddl_path or (
            Path(__file__).resolve().parents[3] / "sql/sqlite/0001_initial.sql"
        )
        self._connection.execute("PRAGMA foreign_keys = ON")

    def close(self) -> None:
        if self._owns_connection:
            self._connection.close()

    def initialize(self) -> None:
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.executescript(self._ddl_path.read_text(encoding="utf-8"))
        rows = dict(
            cast(
                list[tuple[str, str]],
                self._connection.execute(
                    "SELECT metadata_key, metadata_value FROM schema_metadata"
                ).fetchall(),
            )
        )
        unexpected = set(rows) - set(_METADATA)
        conflicts = {
            key for key, value in rows.items() if _METADATA.get(key) != value
        }
        if unexpected or conflicts:
            raise StorageError(
                "RAPTOR.STORAGE.SCHEMA_VERSION: unsupported schema metadata"
            )

    def contains(self, key: ArtifactKey) -> bool:
        row = self._connection.execute(
            "SELECT 1 FROM artifacts WHERE repository_id = ? AND artifact_id = ?",
            key.sort_key(),
        ).fetchone()
        return row is not None

    def _artifact_owner(
        self, key: tuple[str, str]
    ) -> tuple[str, str] | None:
        row = self._connection.execute(
            """
            SELECT repository_id, document_id
            FROM document_artifacts
            WHERE repository_id = ? AND artifact_id = ?
            """,
            key,
        ).fetchone()
        return cast(tuple[str, str] | None, row)

    def put_document(self, document: SourceDocument) -> None:
        self.put_documents((document,))

    def put_documents(self, documents: Iterable[SourceDocument]) -> None:
        staged = tuple(
            SourceDocument.model_validate(document.model_dump(mode="python"))
            for document in documents
        )
        if not staged:
            return
        document_keys = {
            (
                document.provenance.origin.repository_id,
                document.provenance.origin.document_id,
            )
            for document in staged
        }
        if len(document_keys) != len(staged):
            raise StorageError("RAPTOR.STORAGE.DUPLICATE_DOCUMENT: duplicate staged key")
        artifact_keys = set().union(*(_artifact_keys(document) for document in staged))
        resolver = _OverlayResolver(self, artifact_keys, document_keys)
        validate_documents(
            staged, reference_mode=ReferenceValidationMode.STORE, resolver=resolver
        )
        for document in staged:
            self._validate_replacement(document)

        old_by_document = {
            key: self._document_artifact_keys(key) for key in document_keys
        }
        old_source_keys = set().union(*old_by_document.values())
        removed = old_source_keys - artifact_keys
        self._reject_external_inbound(removed, old_source_keys)

        try:
            self._connection.execute("BEGIN IMMEDIATE")
            for document in staged:
                self._write_document_row(document)
            for repository_id, artifact_id in old_source_keys:
                self._connection.execute(
                    "DELETE FROM artifact_relationships WHERE source_repository_id = ? AND source_artifact_id = ?",
                    (repository_id, artifact_id),
                )
                self._connection.execute(
                    "DELETE FROM artifact_uri_relationships WHERE source_repository_id = ? AND source_artifact_id = ?",
                    (repository_id, artifact_id),
                )
            for repository_id, document_id in document_keys:
                self._connection.execute(
                    "DELETE FROM document_artifacts WHERE repository_id = ? AND document_id = ?",
                    (repository_id, document_id),
                )
            for key in removed:
                self._connection.execute(
                    "DELETE FROM artifacts WHERE repository_id = ? AND artifact_id = ?", key
                )
            for document in staged:
                self._write_artifact_rows(document)
            for document in staged:
                self._write_relationships(document)
            self._connection.commit()
        except Exception:
            self._connection.rollback()
            raise

    def _validate_replacement(self, document: SourceDocument) -> None:
        key = _document_key(document)
        row = self._connection.execute(
            "SELECT 1 FROM source_documents WHERE repository_id = ? AND document_id = ?",
            (key.repository_id, key.document_id),
        ).fetchone()
        if row is None:
            return
        previous = self.get_document(key)
        if dump_canonical_json(previous) == dump_canonical_json(document):
            return
        if previous.provenance.origin != document.provenance.origin:
            raise StorageError(
                "RAPTOR.STORAGE.PROVENANCE_TRANSITION: origin is immutable"
            )
        if previous.provenance.materialization == document.provenance.materialization:
            return
        try:
            validate_provenance_transition(previous.provenance, document.provenance)
        except ValueError as error:
            raise StorageError(
                "RAPTOR.STORAGE.PROVENANCE_TRANSITION: invalid materialization transition"
            ) from error

    def _document_artifact_keys(
        self, key: tuple[str, str]
    ) -> set[tuple[str, str]]:
        rows = self._connection.execute(
            """
            SELECT repository_id, artifact_id FROM document_artifacts
            WHERE repository_id = ? AND document_id = ?
            """,
            key,
        ).fetchall()
        return set(cast(list[tuple[str, str]], rows))

    def _reject_external_inbound(
        self,
        removed: set[tuple[str, str]],
        replaced_sources: set[tuple[str, str]],
    ) -> None:
        for target in removed:
            rows = self._connection.execute(
                """
                SELECT source_repository_id, source_artifact_id
                FROM artifact_relationships
                WHERE target_repository_id = ? AND target_artifact_id = ?
                """,
                target,
            ).fetchall()
            if any(tuple(row) not in replaced_sources for row in rows):
                raise StorageError(
                    "RAPTOR.STORAGE.REFERENCE_CONFLICT: artifact has inbound references"
                )

    def _write_document_row(self, document: SourceDocument) -> None:
        origin = document.provenance.origin
        materialization = document.provenance.materialization
        self._connection.execute(
            "INSERT OR IGNORE INTO repositories(repository_id) VALUES (?)",
            (origin.repository_id,),
        )
        self._connection.execute(
            """
            INSERT INTO source_documents(
              repository_id, document_id, current_path, schema_version,
              origin_json, materialization_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(repository_id, document_id) DO UPDATE SET
              current_path = excluded.current_path,
              schema_version = excluded.schema_version,
              origin_json = excluded.origin_json,
              materialization_json = excluded.materialization_json
            """,
            (
                origin.repository_id,
                origin.document_id,
                materialization.repository_path,
                document.schema_version,
                _json(origin),
                _json(materialization),
            ),
        )

    def _write_artifact_rows(self, document: SourceDocument) -> None:
        repository_id = document.provenance.origin.repository_id
        document_id = document.provenance.origin.document_id
        for ordinal, artifact in enumerate(document.artifacts):
            self._connection.execute(
                """
                INSERT INTO artifacts(
                  repository_id, artifact_id, artifact_type, status, artifact_json
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(repository_id, artifact_id) DO UPDATE SET
                  artifact_type = excluded.artifact_type,
                  status = excluded.status,
                  artifact_json = excluded.artifact_json
                """,
                (
                    repository_id,
                    artifact.id,
                    artifact.artifact_type.value,
                    artifact.status.value,
                    _json(artifact),
                ),
            )
            self._connection.execute(
                """
                INSERT INTO document_artifacts(
                  repository_id, document_id, artifact_id, ordinal
                ) VALUES (?, ?, ?, ?)
                """,
                (repository_id, document_id, artifact.id, ordinal),
            )

    def _write_relationships(self, document: SourceDocument) -> None:
        typed, uris = _relationship_rows(document)
        self._connection.executemany(
            """
            INSERT INTO artifact_relationships(
              source_repository_id, source_artifact_id, relation,
              target_repository_id, target_artifact_id, description
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            tuple(typed),
        )
        self._connection.executemany(
            """
            INSERT INTO artifact_uri_relationships(
              source_repository_id, source_artifact_id, relation, target_uri, description
            ) VALUES (?, ?, ?, ?, ?)
            """,
            tuple(uris),
        )

    def get_document(self, key: DocumentKey) -> SourceDocument:
        row = self._connection.execute(
            """
            SELECT current_path, schema_version, origin_json, materialization_json
            FROM source_documents WHERE repository_id = ? AND document_id = ?
            """,
            (key.repository_id, key.document_id),
        ).fetchone()
        if row is None:
            raise KeyError((key.repository_id, key.document_id))
        current_path, schema_version, origin_json, materialization_json = cast(
            tuple[str, str, str, str], row
        )
        artifact_rows = cast(
            list[tuple[str, str, str, str, int]],
            self._connection.execute(
                """
                SELECT a.artifact_id, a.artifact_type, a.status, a.artifact_json, da.ordinal
                FROM document_artifacts AS da
                JOIN artifacts AS a
                  ON a.repository_id = da.repository_id AND a.artifact_id = da.artifact_id
                WHERE da.repository_id = ? AND da.document_id = ?
                ORDER BY da.ordinal
                """,
                (key.repository_id, key.document_id),
            ).fetchall(),
        )
        if [row[4] for row in artifact_rows] != list(range(len(artifact_rows))):
            raise StorageError("RAPTOR.STORAGE.PROJECTION_MISMATCH: invalid ordinals")
        payload = {
            "schema_version": schema_version,
            "provenance": {
                "origin": json.loads(origin_json),
                "materialization": json.loads(materialization_json),
            },
            "artifacts": [json.loads(item[3]) for item in artifact_rows],
        }
        document = validate_document(
            SourceDocument.model_validate(payload),
            reference_mode=ReferenceValidationMode.STRUCTURAL,
        )
        origin = document.provenance.origin
        materialization = document.provenance.materialization
        if (
            origin.repository_id != key.repository_id
            or origin.document_id != key.document_id
            or materialization.repository_path != current_path
            or _json(origin) != origin_json
            or _json(materialization) != materialization_json
        ):
            raise StorageError("RAPTOR.STORAGE.PROJECTION_MISMATCH: document projection")
        for artifact, stored in zip(document.artifacts, artifact_rows, strict=True):
            if (
                artifact.id != stored[0]
                or artifact.artifact_type.value != stored[1]
                or artifact.status.value != stored[2]
                or _json(artifact) != stored[3]
            ):
                raise StorageError("RAPTOR.STORAGE.PROJECTION_MISMATCH: artifact projection")
        expected_typed, expected_uris = _relationship_rows(document)
        source_ids = [artifact.id for artifact in document.artifacts]
        actual_typed = self._typed_rows(key.repository_id, source_ids)
        actual_uris = self._uri_rows(key.repository_id, source_ids)
        if expected_typed != actual_typed or expected_uris != actual_uris:
            raise StorageError("RAPTOR.STORAGE.PROJECTION_MISMATCH: relationship projection")
        return document

    def _typed_rows(
        self, repository_id: str, source_ids: list[str]
    ) -> set[tuple[str, str, str, str, str, str | None]]:
        if not source_ids:
            return set()
        placeholders = ",".join("?" for _ in source_ids)
        rows = self._connection.execute(
            f"""
            SELECT source_repository_id, source_artifact_id, relation,
                   target_repository_id, target_artifact_id, description
            FROM artifact_relationships
            WHERE source_repository_id = ? AND source_artifact_id IN ({placeholders})
            """,
            (repository_id, *source_ids),
        ).fetchall()
        return set(cast(list[tuple[str, str, str, str, str, str | None]], rows))

    def _uri_rows(
        self, repository_id: str, source_ids: list[str]
    ) -> set[tuple[str, str, str, str, str | None]]:
        if not source_ids:
            return set()
        placeholders = ",".join("?" for _ in source_ids)
        rows = self._connection.execute(
            f"""
            SELECT source_repository_id, source_artifact_id, relation,
                   target_uri, description
            FROM artifact_uri_relationships
            WHERE source_repository_id = ? AND source_artifact_id IN ({placeholders})
            """,
            (repository_id, *source_ids),
        ).fetchall()
        return set(cast(list[tuple[str, str, str, str, str | None]], rows))

    def delete_document(self, key: DocumentKey) -> None:
        source_keys = self._document_artifact_keys(
            (key.repository_id, key.document_id)
        )
        if not source_keys:
            if self._connection.execute(
                "SELECT 1 FROM source_documents WHERE repository_id = ? AND document_id = ?",
                (key.repository_id, key.document_id),
            ).fetchone() is None:
                raise KeyError((key.repository_id, key.document_id))
        self._reject_external_inbound(source_keys, source_keys)
        try:
            self._connection.execute("BEGIN IMMEDIATE")
            for artifact_key in source_keys:
                self._connection.execute(
                    "DELETE FROM artifact_relationships WHERE source_repository_id = ? AND source_artifact_id = ?",
                    artifact_key,
                )
                self._connection.execute(
                    "DELETE FROM artifact_uri_relationships WHERE source_repository_id = ? AND source_artifact_id = ?",
                    artifact_key,
                )
            self._connection.execute(
                "DELETE FROM document_artifacts WHERE repository_id = ? AND document_id = ?",
                (key.repository_id, key.document_id),
            )
            for artifact_key in source_keys:
                self._connection.execute(
                    "DELETE FROM artifacts WHERE repository_id = ? AND artifact_id = ?",
                    artifact_key,
                )
            self._connection.execute(
                "DELETE FROM source_documents WHERE repository_id = ? AND document_id = ?",
                (key.repository_id, key.document_id),
            )
            self._connection.commit()
        except Exception:
            self._connection.rollback()
            raise

    def list_artifact_keys(
        self,
        *,
        repository_id: RepositoryId | None = None,
        artifact_type: str | None = None,
    ) -> list[ArtifactKey]:
        clauses: list[str] = []
        parameters: list[str] = []
        if repository_id is not None:
            clauses.append("repository_id = ?")
            parameters.append(repository_id)
        if artifact_type is not None:
            clauses.append("artifact_type = ?")
            parameters.append(artifact_type)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._connection.execute(
            f"SELECT repository_id, artifact_id FROM artifacts{where} ORDER BY repository_id, artifact_id",
            parameters,
        ).fetchall()
        return [
            ArtifactKey(repository_id=row[0], artifact_id=row[1]) for row in rows
        ]


__all__ = [
    "DATABASE_SCHEMA_VERSION",
    "MODEL_SCHEMA_VERSION",
    "SQLiteArtifactStore",
    "StorageError",
]
