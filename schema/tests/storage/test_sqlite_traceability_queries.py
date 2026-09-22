from __future__ import annotations

from raptor_schema import SQLiteArtifactStore, SourceDocument


def test_forward_reverse_typed_and_uri_traceability_queries(document: SourceDocument) -> None:
    store = SQLiteArtifactStore()
    store.initialize()
    store.put_document(document)
    repository_id = document.provenance.origin.repository_id
    typed_source_id = document.artifacts[1].id
    uri_source_id = document.artifacts[0].id
    typed = store._connection.execute(
        "SELECT relation, target_artifact_id FROM artifact_relationships "
        "WHERE source_repository_id = ? AND source_artifact_id = ? ORDER BY relation, target_artifact_id",
        (repository_id, typed_source_id),
    ).fetchall()
    reverse = store._connection.execute(
        "SELECT relation, source_artifact_id FROM artifact_relationships "
        "WHERE target_repository_id = ? AND target_artifact_id = ? ORDER BY relation, source_artifact_id",
        (repository_id, uri_source_id),
    ).fetchall()
    uris = store._connection.execute(
        "SELECT relation, target_uri FROM artifact_uri_relationships "
        "WHERE source_repository_id = ? AND source_artifact_id = ?",
        (repository_id, uri_source_id),
    ).fetchall()

    assert typed and reverse and uris
