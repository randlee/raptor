from __future__ import annotations

import json
import hashlib
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import cast

from pydantic import JsonValue

from .._references import iter_canonical_references
from ..canonical import (
    ReferenceValidationMode,
    _encode_canonical_value,
    dump_canonical_fragment,
    dump_canonical_json,
    validate_document,
    validate_documents,
)
from ..models import (
    ArtifactKey,
    DocumentKey,
    RepositoryId,
    RelationshipType,
    SourceDocument,
    validate_provenance_transition,
)
from .base import StorageError, document_key

DATABASE_SCHEMA_VERSION = "1"
MODEL_SCHEMA_VERSION = "1.0.0"
_METADATA = {
    "database_schema_version": DATABASE_SCHEMA_VERSION,
    "canonical_model_schema_version": MODEL_SCHEMA_VERSION,
}


def _membership(document: SourceDocument) -> tuple[int, str]:
    artifact_ids = [artifact.id for artifact in document.artifacts]
    encoded = _encode_canonical_value(cast(JsonValue, artifact_ids))
    return len(artifact_ids), hashlib.sha256(encoded.encode()).hexdigest()


def _artifact_keys(document: SourceDocument) -> set[tuple[str, str]]:
    repository_id = document.provenance.origin.repository_id
    return {(repository_id, artifact.id) for artifact in document.artifacts}


def _relationship_rows(
    document: SourceDocument,
) -> tuple[
    set[tuple[str, str, str, str, str, str | None]],
    set[tuple[str, str, str, str, str | None]],
]:
    typed_by_key: dict[tuple[str, str, str, str, str], str | None] = {}
    uris: set[tuple[str, str, str, str, str | None]] = set()
    for reference in iter_canonical_references(document):
        target = reference.target
        if isinstance(target, ArtifactKey):
            # Explicit relationships are yielded before family-derived edges.
            # One SQL row represents one semantic edge, so retain the explicit
            # description when both forms describe the same edge.
            typed_by_key.setdefault(
                (
                    reference.source.repository_id,
                    reference.source.artifact_id,
                    reference.relation,
                    target.repository_id,
                    target.artifact_id,
                ),
                reference.description,
            )
        else:
            uris.add(
                (
                    reference.source.repository_id,
                    reference.source.artifact_id,
                    reference.relation,
                    target,
                    reference.description,
                )
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


@dataclass(frozen=True)
class TypedTraceabilityEdge:
    source: ArtifactKey
    relation: RelationshipType
    target: ArtifactKey


@dataclass(frozen=True)
class UriTraceabilityEdge:
    source: ArtifactKey
    relation: RelationshipType
    target_uri: str


@dataclass(frozen=True)
class TraceabilityRelationships:
    typed: tuple[TypedTraceabilityEdge, ...]
    uri: tuple[UriTraceabilityEdge, ...]

    @property
    def typed_count(self) -> int:
        return len(self.typed)

    @property
    def uri_count(self) -> int:
        return len(self.uri)

    @property
    def total_count(self) -> int:
        return self.typed_count + self.uri_count


class SQLiteArtifactStore:
    def __init__(self, database: str | Path = ":memory:") -> None:
        if not isinstance(database, (str, Path)):
            raise TypeError("database must be a store-owned path or ':memory:'")
        self._connection = sqlite3.connect(str(database), isolation_level=None)
        self._connection.execute("PRAGMA foreign_keys = ON")

    @classmethod
    def open_read_only(cls, database: str | Path) -> "SQLiteArtifactStore":
        path = Path(database).resolve()
        instance = cls.__new__(cls)
        instance._connection = sqlite3.connect(
            f"{path.as_uri()}?mode=ro&immutable=1", uri=True, isolation_level=None
        )
        instance._connection.execute("PRAGMA foreign_keys = ON")
        return instance

    def close(self) -> None:
        self._connection.close()

    def _require_foreign_keys(self) -> None:
        if self._connection.execute("PRAGMA foreign_keys").fetchone() != (1,):
            raise StorageError(
                "RAPTOR.STORAGE.FOREIGN_KEYS_DISABLED: foreign keys are required"
            )

    @staticmethod
    def _integrity_error(error: sqlite3.IntegrityError) -> StorageError:
        message = str(error)
        if "source_documents.repository_id, source_documents.current_path" in message:
            code = "RAPTOR.STORAGE.PATH_CONFLICT"
        elif (
            "document_artifacts.repository_id, document_artifacts.artifact_id"
            in message
        ):
            code = "RAPTOR.STORAGE.ARTIFACT_CONFLICT"
        elif "FOREIGN KEY constraint failed" in message:
            code = "RAPTOR.STORAGE.REFERENCE_CONFLICT"
        else:
            code = "RAPTOR.STORAGE.INTEGRITY_CONFLICT"
        return StorageError(f"{code}: SQLite rejected the storage projection")

    @staticmethod
    def _ddl() -> str:
        resource = files("raptor_schema").joinpath("sql/sqlite/0001_initial.sql")
        try:
            return resource.read_text(encoding="utf-8")
        except FileNotFoundError:
            source = Path(__file__).resolve().parents[3] / "sql/sqlite/0001_initial.sql"
            return source.read_text(encoding="utf-8")

    def initialize(self) -> None:
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._require_foreign_keys()
        existed = self._connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'schema_metadata'"
        ).fetchone()
        if existed is not None:
            self._validate_metadata()
        self._connection.executescript(self._ddl())
        self._validate_metadata()

    def _validate_metadata(self) -> None:
        rows = dict(
            cast(
                list[tuple[str, str]],
                self._connection.execute(
                    "SELECT metadata_key, metadata_value FROM schema_metadata"
                ).fetchall(),
            )
        )
        if rows != _METADATA:
            raise StorageError(
                "RAPTOR.STORAGE.SCHEMA_VERSION: unsupported schema metadata"
            )

    def list_document_keys(self) -> list[DocumentKey]:
        self._require_foreign_keys()
        rows = cast(
            list[tuple[str, str]],
            self._connection.execute(
                "SELECT repository_id, document_id FROM source_documents "
                "ORDER BY repository_id, document_id"
            ).fetchall(),
        )
        return [
            DocumentKey(repository_id=repository_id, document_id=document_id)
            for repository_id, document_id in rows
        ]

    def traceability_relationships(
        self, key: DocumentKey
    ) -> TraceabilityRelationships:
        """Return the stored typed and URI edges emitted by one document."""
        self._require_foreign_keys()
        typed_rows = cast(
            list[tuple[str, str, str, str, str]],
            self._connection.execute(
                """
                SELECT relationship.source_repository_id,
                       relationship.source_artifact_id,
                       relationship.relation,
                       relationship.target_repository_id,
                       relationship.target_artifact_id
                FROM artifact_relationships AS relationship
                JOIN document_artifacts AS membership
                  ON membership.repository_id = relationship.source_repository_id
                 AND membership.artifact_id = relationship.source_artifact_id
                WHERE membership.repository_id = ? AND membership.document_id = ?
                ORDER BY relationship.source_repository_id,
                         relationship.source_artifact_id,
                         relationship.relation,
                         relationship.target_repository_id,
                         relationship.target_artifact_id
                """,
                (key.repository_id, key.document_id),
            ).fetchall(),
        )
        uri_rows = cast(
            list[tuple[str, str, str, str]],
            self._connection.execute(
                """
                SELECT relationship.source_repository_id,
                       relationship.source_artifact_id,
                       relationship.relation,
                       relationship.target_uri
                FROM artifact_uri_relationships AS relationship
                JOIN document_artifacts AS membership
                  ON membership.repository_id = relationship.source_repository_id
                 AND membership.artifact_id = relationship.source_artifact_id
                WHERE membership.repository_id = ? AND membership.document_id = ?
                ORDER BY relationship.source_repository_id,
                         relationship.source_artifact_id,
                         relationship.relation,
                         relationship.target_uri
                """,
                (key.repository_id, key.document_id),
            ).fetchall(),
        )
        return TraceabilityRelationships(
            typed=tuple(
                TypedTraceabilityEdge(
                    source=ArtifactKey(repository_id=row[0], artifact_id=row[1]),
                    relation=RelationshipType(row[2]),
                    target=ArtifactKey(repository_id=row[3], artifact_id=row[4]),
                )
                for row in typed_rows
            ),
            uri=tuple(
                UriTraceabilityEdge(
                    source=ArtifactKey(repository_id=row[0], artifact_id=row[1]),
                    relation=RelationshipType(row[2]),
                    target_uri=row[3],
                )
                for row in uri_rows
            ),
        )

    def reverse_typed_relationships(
        self, target: ArtifactKey
    ) -> tuple[TypedTraceabilityEdge, ...]:
        """Return typed edges that target one artifact."""
        self._require_foreign_keys()
        rows = cast(
            list[tuple[str, str, str, str, str]],
            self._connection.execute(
                """
                SELECT source_repository_id,
                       source_artifact_id,
                       relation,
                       target_repository_id,
                       target_artifact_id
                FROM artifact_relationships
                WHERE target_repository_id = ? AND target_artifact_id = ?
                ORDER BY source_repository_id,
                         source_artifact_id,
                         relation,
                         target_repository_id,
                         target_artifact_id
                """,
                target.sort_key(),
            ).fetchall(),
        )
        return tuple(
            TypedTraceabilityEdge(
                source=ArtifactKey(repository_id=row[0], artifact_id=row[1]),
                relation=RelationshipType(row[2]),
                target=ArtifactKey(repository_id=row[3], artifact_id=row[4]),
            )
            for row in rows
        )

    def validate(self) -> None:
        self._require_foreign_keys()
        self._validate_metadata()
        if self._connection.execute("PRAGMA integrity_check").fetchone() != ("ok",):
            raise StorageError(
                "RAPTOR.STORAGE.INTEGRITY_CONFLICT: integrity check failed"
            )
        if self._connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise StorageError(
                "RAPTOR.STORAGE.INTEGRITY_CONFLICT: foreign key check failed"
            )
        for key in self.list_document_keys():
            self.get_document(key)

    def contains(self, key: ArtifactKey) -> bool:
        self._require_foreign_keys()
        row = self._connection.execute(
            "SELECT 1 FROM artifacts WHERE repository_id = ? AND artifact_id = ?",
            key.sort_key(),
        ).fetchone()
        return row is not None

    def _artifact_owner(self, key: tuple[str, str]) -> tuple[str, str] | None:
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
        self._require_foreign_keys()
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
            raise StorageError(
                "RAPTOR.STORAGE.DUPLICATE_DOCUMENT: duplicate staged key"
            )
        artifact_keys = set().union(*(_artifact_keys(document) for document in staged))
        try:
            self._connection.execute("BEGIN IMMEDIATE")
            resolver = _OverlayResolver(self, artifact_keys, document_keys)
            validate_documents(
                staged,
                reference_mode=ReferenceValidationMode.STORE,
                resolver=resolver,
            )
            for document in staged:
                self._validate_replacement(document)
            old_source_keys = set().union(
                *(self._document_artifact_keys(key) for key in document_keys)
            )
            removed = old_source_keys - artifact_keys
            retained = old_source_keys & artifact_keys
            self._reject_external_inbound(removed, old_source_keys)
            for document in staged:
                self._write_document_row(document)
            for repository_id, artifact_id in old_source_keys:
                self._connection.execute(
                    "DELETE FROM artifact_relationships WHERE source_repository_id = ? AND source_artifact_id = ?",
                    (repository_id, artifact_id),
                )
            for repository_id, artifact_id in retained:
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
                    "DELETE FROM artifacts WHERE repository_id = ? AND artifact_id = ?",
                    key,
                )
            for document in staged:
                self._write_artifact_rows(document)
            for document in staged:
                self._write_relationships(document)
            self._connection.commit()
        except sqlite3.IntegrityError as error:
            self._connection.rollback()
            raise self._integrity_error(error) from error
        except Exception:
            self._connection.rollback()
            raise

    def _validate_replacement(self, document: SourceDocument) -> None:
        key = document_key(document)
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
        try:
            validate_provenance_transition(previous.provenance, document.provenance)
        except ValueError as error:
            raise StorageError(
                "RAPTOR.STORAGE.PROVENANCE_TRANSITION: invalid materialization transition"
            ) from error

    def _document_artifact_keys(self, key: tuple[str, str]) -> set[tuple[str, str]]:
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
        artifact_count, membership_sha256 = _membership(document)
        canonical_sha256 = hashlib.sha256(
            dump_canonical_json(document).encode()
        ).hexdigest()
        self._connection.execute(
            "INSERT OR IGNORE INTO repositories(repository_id) VALUES (?)",
            (origin.repository_id,),
        )
        self._connection.execute(
            """
            INSERT INTO source_documents(
              repository_id, document_id, current_path, schema_version,
              artifact_count, membership_sha256, canonical_sha256,
              origin_json, materialization_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(repository_id, document_id) DO UPDATE SET
              current_path = excluded.current_path,
              schema_version = excluded.schema_version,
              artifact_count = excluded.artifact_count,
              membership_sha256 = excluded.membership_sha256,
              canonical_sha256 = excluded.canonical_sha256,
              origin_json = excluded.origin_json,
              materialization_json = excluded.materialization_json
            """,
            (
                origin.repository_id,
                origin.document_id,
                materialization.repository_path,
                document.schema_version,
                artifact_count,
                membership_sha256,
                canonical_sha256,
                dump_canonical_fragment(origin),
                dump_canonical_fragment(materialization),
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
                    dump_canonical_fragment(artifact),
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
        self._require_foreign_keys()
        row = self._connection.execute(
            """
            SELECT current_path, schema_version, artifact_count, membership_sha256,
                   canonical_sha256, origin_json, materialization_json
            FROM source_documents WHERE repository_id = ? AND document_id = ?
            """,
            (key.repository_id, key.document_id),
        ).fetchone()
        if row is None:
            if (
                self._connection.execute(
                    "SELECT 1 FROM document_artifacts WHERE repository_id = ? AND document_id = ? LIMIT 1",
                    (key.repository_id, key.document_id),
                ).fetchone()
                is not None
            ):
                raise StorageError(
                    "RAPTOR.STORAGE.FOREIGN_KEY_VIOLATION: document parent is missing"
                )
            raise KeyError((key.repository_id, key.document_id))
        if (
            self._connection.execute(
                "SELECT 1 FROM repositories WHERE repository_id = ?",
                (key.repository_id,),
            ).fetchone()
            is None
        ):
            raise StorageError(
                "RAPTOR.STORAGE.FOREIGN_KEY_VIOLATION: repository parent is missing"
            )
        (
            current_path,
            schema_version,
            expected_count,
            expected_membership,
            expected_canonical_sha256,
            origin_json,
            materialization_json,
        ) = cast(tuple[str, str, int, str, str, str, str], row)
        if (
            self._connection.execute(
                """
            SELECT 1 FROM document_artifacts AS membership
            LEFT JOIN artifacts AS artifact
              ON artifact.repository_id = membership.repository_id
             AND artifact.artifact_id = membership.artifact_id
            WHERE membership.repository_id = ? AND membership.document_id = ?
              AND artifact.artifact_id IS NULL LIMIT 1
            """,
                (key.repository_id, key.document_id),
            ).fetchone()
            is not None
        ):
            raise StorageError(
                "RAPTOR.STORAGE.FOREIGN_KEY_VIOLATION: artifact parent is missing"
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
        actual_membership = hashlib.sha256(
            _encode_canonical_value([row[0] for row in artifact_rows]).encode()
        ).hexdigest()
        if (
            len(artifact_rows) != expected_count
            or actual_membership != expected_membership
        ):
            raise StorageError(
                "RAPTOR.STORAGE.PROJECTION_MISMATCH: membership projection"
            )
        if (
            self._connection.execute(
                """
            SELECT 1 FROM artifacts AS a
            LEFT JOIN document_artifacts AS da
              ON da.repository_id = a.repository_id AND da.artifact_id = a.artifact_id
            WHERE a.repository_id = ? AND da.artifact_id IS NULL LIMIT 1
            """,
                (key.repository_id,),
            ).fetchone()
            is not None
        ):
            raise StorageError("RAPTOR.STORAGE.PROJECTION_MISMATCH: orphan artifact")
        try:
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
        except (TypeError, ValueError) as error:
            raise StorageError(
                "RAPTOR.STORAGE.PROJECTION_MISMATCH: invalid canonical JSON"
            ) from error
        if (
            hashlib.sha256(dump_canonical_json(document).encode()).hexdigest()
            != expected_canonical_sha256
        ):
            raise StorageError(
                "RAPTOR.STORAGE.PROJECTION_MISMATCH: canonical document digest"
            )
        origin = document.provenance.origin
        materialization = document.provenance.materialization
        if (
            origin.repository_id != key.repository_id
            or origin.document_id != key.document_id
            or materialization.repository_path != current_path
            or dump_canonical_fragment(origin) != origin_json
            or dump_canonical_fragment(materialization) != materialization_json
        ):
            raise StorageError(
                "RAPTOR.STORAGE.PROJECTION_MISMATCH: document projection"
            )
        for artifact, stored in zip(document.artifacts, artifact_rows, strict=True):
            if (
                artifact.id != stored[0]
                or artifact.artifact_type.value != stored[1]
                or artifact.status.value != stored[2]
                or dump_canonical_fragment(artifact) != stored[3]
            ):
                raise StorageError(
                    "RAPTOR.STORAGE.PROJECTION_MISMATCH: artifact projection"
                )
        expected_typed, expected_uris = _relationship_rows(document)
        source_ids = [artifact.id for artifact in document.artifacts]
        self._check_relationship_foreign_keys(key.repository_id, source_ids)
        actual_typed = self._typed_rows(key.repository_id, source_ids)
        actual_uris = self._uri_rows(key.repository_id, source_ids)
        if expected_typed != actual_typed or expected_uris != actual_uris:
            raise StorageError(
                "RAPTOR.STORAGE.PROJECTION_MISMATCH: relationship projection"
            )
        return document

    def _check_relationship_foreign_keys(
        self, repository_id: str, source_ids: list[str]
    ) -> None:
        if not source_ids:
            return
        placeholders = ",".join("?" for _ in source_ids)
        row = self._connection.execute(
            f"""
            SELECT 1
            FROM artifact_relationships AS relationship
            LEFT JOIN artifacts AS source
              ON source.repository_id = relationship.source_repository_id
             AND source.artifact_id = relationship.source_artifact_id
            LEFT JOIN artifacts AS target
              ON target.repository_id = relationship.target_repository_id
             AND target.artifact_id = relationship.target_artifact_id
            LEFT JOIN document_artifacts AS target_membership
              ON target_membership.repository_id = relationship.target_repository_id
             AND target_membership.artifact_id = relationship.target_artifact_id
            LEFT JOIN source_documents AS target_document
              ON target_document.repository_id = target_membership.repository_id
             AND target_document.document_id = target_membership.document_id
            LEFT JOIN repositories AS target_repository
              ON target_repository.repository_id = relationship.target_repository_id
            WHERE relationship.source_repository_id = ?
              AND relationship.source_artifact_id IN ({placeholders})
              AND (
                source.artifact_id IS NULL OR target.artifact_id IS NULL
                OR target_membership.artifact_id IS NULL
                OR target_document.document_id IS NULL
                OR target_repository.repository_id IS NULL
              )
            LIMIT 1
            """,
            (repository_id, *source_ids),
        ).fetchone()
        if row is not None:
            raise StorageError(
                "RAPTOR.STORAGE.FOREIGN_KEY_VIOLATION: relationship endpoint is missing"
            )

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
        self._require_foreign_keys()
        try:
            self._connection.execute("BEGIN IMMEDIATE")
            source_keys = self._document_artifact_keys(
                (key.repository_id, key.document_id)
            )
            if (
                not source_keys
                and self._connection.execute(
                    "SELECT 1 FROM source_documents WHERE repository_id = ? AND document_id = ?",
                    (key.repository_id, key.document_id),
                ).fetchone()
                is None
            ):
                raise KeyError((key.repository_id, key.document_id))
            self._reject_external_inbound(source_keys, source_keys)
            for artifact_key in source_keys:
                self._connection.execute(
                    "DELETE FROM artifact_relationships WHERE source_repository_id = ? AND source_artifact_id = ?",
                    artifact_key,
                )
            self._connection.execute(
                "DELETE FROM source_documents WHERE repository_id = ? AND document_id = ?",
                (key.repository_id, key.document_id),
            )
            for artifact_key in source_keys:
                self._connection.execute(
                    "DELETE FROM artifacts WHERE repository_id = ? AND artifact_id = ?",
                    artifact_key,
                )
            self._connection.commit()
        except sqlite3.IntegrityError as error:
            self._connection.rollback()
            raise self._integrity_error(error) from error
        except Exception:
            self._connection.rollback()
            raise

    def list_artifact_keys(
        self,
        *,
        repository_id: RepositoryId | None = None,
        artifact_type: str | None = None,
    ) -> list[ArtifactKey]:
        self._require_foreign_keys()
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
        return [ArtifactKey(repository_id=row[0], artifact_id=row[1]) for row in rows]


__all__ = [
    "DATABASE_SCHEMA_VERSION",
    "MODEL_SCHEMA_VERSION",
    "SQLiteArtifactStore",
    "StorageError",
    "TraceabilityRelationships",
    "TypedTraceabilityEdge",
    "UriTraceabilityEdge",
]
