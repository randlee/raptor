from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

from ..canonical import dump_canonical_fragment, dump_canonical_json
from ..models import ArtifactKey, DocumentKey, RepositoryId, SourceDocument
from .base import StorageError, document_key

DATABASE_SCHEMA_VERSION = "2"
MODEL_SCHEMA_VERSION = "2.0.0"
_METADATA = {"database_schema_version": DATABASE_SCHEMA_VERSION, "canonical_model_schema_version": MODEL_SCHEMA_VERSION}


@dataclass(frozen=True)
class TraceabilityRelationship:
    source: ArtifactKey
    relation_type: str
    target_token: str
    context: str
    target: ArtifactKey | None


@dataclass(frozen=True)
class TraceabilityRelationships:
    relationships: tuple[TraceabilityRelationship, ...]

    @property
    def total_count(self) -> int:
        return len(self.relationships)


class SQLiteArtifactStore:
    def __init__(self, database: str | Path = ":memory:") -> None:
        self._connection = sqlite3.connect(str(database), isolation_level=None)
        self._connection.execute("PRAGMA foreign_keys = ON")

    @classmethod
    def open_read_only(cls, database: str | Path) -> "SQLiteArtifactStore":
        path = Path(database).resolve()
        instance = cls.__new__(cls)
        instance._connection = sqlite3.connect(f"{path.as_uri()}?mode=ro&immutable=1", uri=True, isolation_level=None)
        instance._connection.execute("PRAGMA foreign_keys = ON")
        return instance

    def close(self) -> None:
        self._connection.close()

    @staticmethod
    def _ddl() -> str:
        resource = files("raptor_schema").joinpath("sql/sqlite/0001_initial.sql")
        try:
            return resource.read_text(encoding="utf-8")
        except FileNotFoundError:
            return (Path(__file__).resolve().parents[3] / "sql/sqlite/0001_initial.sql").read_text(encoding="utf-8")

    def initialize(self) -> None:
        exists = self._connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_metadata'").fetchone()
        if exists:
            self._validate_metadata()
        self._connection.executescript(self._ddl())
        self._validate_metadata()

    def _validate_metadata(self) -> None:
        rows = dict(self._connection.execute("SELECT metadata_key, metadata_value FROM schema_metadata"))
        if rows != _METADATA:
            raise StorageError("RAPTOR.STORAGE.SCHEMA_VERSION: unsupported schema metadata")

    def contains(self, key: ArtifactKey) -> bool:
        return self._connection.execute("SELECT 1 FROM artifacts WHERE repository_id=? AND document_id=? AND artifact_id=?", key.sort_key()).fetchone() is not None

    def list_document_keys(self) -> list[DocumentKey]:
        return [DocumentKey(repository_id=row[0], document_id=row[1]) for row in self._connection.execute("SELECT repository_id, document_id FROM documents ORDER BY repository_id, document_id")]

    def list_artifact_keys(self, *, repository_id: RepositoryId | None = None, artifact_type: str | None = None) -> list[ArtifactKey]:
        clauses, values = [], []
        if repository_id is not None:
            clauses.append("repository_id=?"); values.append(repository_id)
        if artifact_type is not None:
            clauses.append("artifact_type=?"); values.append(artifact_type)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        rows = self._connection.execute(f"SELECT repository_id, document_id, artifact_id FROM artifacts{where} ORDER BY repository_id, document_id, ordinal", values)
        return [ArtifactKey(repository_id=row[0], document_id=row[1], artifact_id=row[2]) for row in rows]

    def put_document(self, document: SourceDocument) -> None:
        self.put_documents((document,))

    def put_documents(self, documents: Iterable[SourceDocument]) -> None:
        staged = tuple(SourceDocument.model_validate(item) for item in documents)
        if not staged:
            return
        keys = {(item.provenance.origin.repository_id, item.provenance.origin.document_id) for item in staged}
        if len(keys) != len(staged):
            raise StorageError("RAPTOR.STORAGE.DUPLICATE_DOCUMENT: duplicate staged key")
        try:
            self._connection.execute("BEGIN IMMEDIATE")
            for document in staged:
                self._write_document(document)
            self._resolve_relationships()
            self._connection.commit()
        except sqlite3.IntegrityError as error:
            self._connection.rollback()
            raise StorageError("RAPTOR.STORAGE.INTEGRITY_CONFLICT: SQLite rejected the storage projection") from error
        except Exception:
            self._connection.rollback()
            raise

    def _write_document(self, document: SourceDocument) -> None:
        origin, materialization = document.provenance.origin, document.provenance.materialization
        key = (origin.repository_id, origin.document_id)
        self._connection.execute("INSERT OR IGNORE INTO repositories(repository_id) VALUES (?)", (origin.repository_id,))
        self._connection.execute("DELETE FROM documents WHERE repository_id=? AND document_id=?", key)
        self._connection.execute("""INSERT INTO documents(repository_id, document_id, current_path, schema_version, title, metadata_json, non_item_segments_json, origin_json, materialization_json, canonical_sha256)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (*key, materialization.repository_path, document.schema_version, document.title, json.dumps(document.document_metadata, sort_keys=True), json.dumps([item.model_dump(mode="json", exclude_none=True) for item in document.non_item_segments], sort_keys=True), dump_canonical_fragment(origin), dump_canonical_fragment(materialization), hashlib.sha256(dump_canonical_json(document).encode()).hexdigest()))
        for ordinal, artifact in enumerate(document.artifacts):
            self._connection.execute("""INSERT INTO artifacts(repository_id, document_id, artifact_id, ordinal, artifact_type, title, status, domain, source_json, content_markdown, artifact_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (*key, artifact.id, ordinal, artifact.artifact_type.value, artifact.title, artifact.status.value if artifact.status else None, artifact.domain, json.dumps(artifact.source, sort_keys=True), artifact.content, dump_canonical_fragment(artifact)))
            for relationship_ordinal, relationship in enumerate(artifact.relationships):
                self._connection.execute("""INSERT INTO relationships(source_repository_id, source_document_id, source_artifact_id, ordinal, relation_type, target_token, context, target_repository_id, target_document_id, target_artifact_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL)""", (*key, artifact.id, relationship_ordinal, relationship.relation_type, relationship.target_token, relationship.context))

    def _resolve_relationships(self) -> None:
        self._connection.execute("UPDATE relationships SET target_repository_id=NULL, target_document_id=NULL, target_artifact_id=NULL")
        rows = list(self._connection.execute("SELECT rowid, source_repository_id, target_token FROM relationships"))
        for rowid, repository_id, token in rows:
            matches = list(self._connection.execute("SELECT repository_id, document_id, artifact_id FROM artifacts WHERE repository_id=? AND artifact_id=?", (repository_id, token)))
            if len(matches) == 1:
                self._connection.execute("UPDATE relationships SET target_repository_id=?, target_document_id=?, target_artifact_id=? WHERE rowid=?", (*matches[0], rowid))

    def get_document(self, key: DocumentKey) -> SourceDocument:
        row = self._connection.execute("SELECT title, metadata_json, non_item_segments_json, origin_json, materialization_json FROM documents WHERE repository_id=? AND document_id=?", (key.repository_id, key.document_id)).fetchone()
        if row is None:
            raise KeyError((key.repository_id, key.document_id))
        artifacts = [json.loads(value[0]) for value in self._connection.execute("SELECT artifact_json FROM artifacts WHERE repository_id=? AND document_id=? ORDER BY ordinal", (key.repository_id, key.document_id))]
        return SourceDocument.model_validate({"schema_version": MODEL_SCHEMA_VERSION, "provenance": {"origin": json.loads(row[3]), "materialization": json.loads(row[4])}, "title": row[0], "document_metadata": json.loads(row[1]), "non_item_segments": json.loads(row[2]), "artifacts": artifacts})

    def traceability_relationships(self, key: DocumentKey) -> TraceabilityRelationships:
        rows = self._connection.execute("""SELECT source_repository_id, source_document_id, source_artifact_id, relation_type, target_token, context, target_repository_id, target_document_id, target_artifact_id FROM relationships WHERE source_repository_id=? AND source_document_id=? ORDER BY source_artifact_id, ordinal""", (key.repository_id, key.document_id))
        return TraceabilityRelationships(tuple(TraceabilityRelationship(source=ArtifactKey(repository_id=row[0], document_id=row[1], artifact_id=row[2]), relation_type=row[3], target_token=row[4], context=row[5], target=ArtifactKey(repository_id=row[6], document_id=row[7], artifact_id=row[8]) if row[6] else None) for row in rows))

    def reverse_typed_relationships(self, target: ArtifactKey) -> tuple[TraceabilityRelationship, ...]:
        rows = self._connection.execute("""SELECT source_repository_id, source_document_id, source_artifact_id, relation_type, target_token, context FROM relationships WHERE target_repository_id=? AND target_document_id=? AND target_artifact_id=? ORDER BY source_repository_id, source_document_id, source_artifact_id, ordinal""", target.sort_key())
        return tuple(TraceabilityRelationship(source=ArtifactKey(repository_id=row[0], document_id=row[1], artifact_id=row[2]), relation_type=row[3], target_token=row[4], context=row[5], target=target) for row in rows)

    def delete_document(self, key: DocumentKey) -> None:
        if self._connection.execute("DELETE FROM documents WHERE repository_id=? AND document_id=?", (key.repository_id, key.document_id)).rowcount == 0:
            raise KeyError((key.repository_id, key.document_id))
        self._resolve_relationships()

    def validate(self) -> None:
        self._validate_metadata()
        if self._connection.execute("PRAGMA integrity_check").fetchone() != ("ok",):
            raise StorageError("RAPTOR.STORAGE.INTEGRITY_CONFLICT: integrity check failed")
        for key in self.list_document_keys():
            self.get_document(key)


__all__ = ["DATABASE_SCHEMA_VERSION", "MODEL_SCHEMA_VERSION", "SQLiteArtifactStore", "StorageError", "TraceabilityRelationship", "TraceabilityRelationships"]
