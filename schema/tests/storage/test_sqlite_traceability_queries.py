from __future__ import annotations

from raptor_schema import (
    ArtifactKey,
    DocumentKey,
    RelationshipType,
    SQLiteArtifactStore,
    SourceDocument,
)


def test_forward_reverse_typed_and_uri_traceability_queries(document: SourceDocument) -> None:
    store = SQLiteArtifactStore()
    store.initialize()
    store.put_document(document)
    repository_id = document.provenance.origin.repository_id
    key = DocumentKey(
        repository_id=repository_id,
        document_id=document.provenance.origin.document_id,
    )
    relationships = store.traceability_relationships(key)
    reverse = store.reverse_typed_relationships(
        ArtifactKey(repository_id=repository_id, artifact_id="REQ-RAP-001")
    )

    typed = {
        (edge.source.artifact_id, edge.relation, edge.target.artifact_id)
        for edge in relationships.typed
    }
    assert ("DES-RAP-001", RelationshipType.DEPENDS_ON, "ADR-RAP-001") in typed
    assert ("TST-RAP-001", RelationshipType.VERIFIES, "REQ-RAP-001") in typed
    assert ("TST-RAP-001", RelationshipType.VERIFIES, "NFR-RAP-004") in typed
    assert any(
        edge.source.artifact_id == "NFR-RAP-004"
        and edge.relation is RelationshipType.SATISFIES
        for edge in reverse
    )
    assert any(
        edge.source.artifact_id == "TST-RAP-001"
        and edge.relation is RelationshipType.VERIFIES
        for edge in reverse
    )
    assert {
        (edge.source.artifact_id, edge.relation, edge.target_uri)
        for edge in relationships.uri
    } == {
        (
            "REQ-RAP-001",
            RelationshipType.RELATES_TO,
            "urn:raptor:contract:v1",
        )
    }
