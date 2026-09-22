from raptor_schema import ArtifactKey, DocumentKey, SQLiteArtifactStore, SourceDocument, document_key


def _document(document_id: str, artifact_id: str, content: str = "\nBody\n") -> SourceDocument:
    digest = "0" * 64
    path = f"docs/{document_id}.md"
    return SourceDocument.model_validate({
        "schema_version": "2.0.0",
        "provenance": {"origin": {"repository_id": "urn:raptor:repo:alpha", "document_id": document_id, "initial_repository_path": path, "original_content_sha256": digest, "source_format": "markdown", "parser_profile": "raptor", "parser_profile_version": "2.0.0"}, "materialization": {"repository_path": path, "content_sha256": digest, "operation": "imported", "parser_profile": "raptor", "parser_profile_version": "2.0.0"}},
        "artifacts": [{"artifact_type": "requirement", "id": artifact_id, "title": artifact_id, "content": content, "relationships": [{"relation_type": "references", "target_token": "REQ-CORE-0002", "context": "reference"}]}],
    })


def test_v2_sqlite_round_trips_and_resolves_unique_emitted_relationship() -> None:
    first, second = _document("DOC-CORE-0001", "REQ-CORE-0001"), _document("DOC-CORE-0002", "REQ-CORE-0002")
    store = SQLiteArtifactStore()
    store.initialize()
    store.put_documents((first, second))
    assert store.get_document(document_key(first)) == first
    relationship = store.traceability_relationships(document_key(first)).relationships[0]
    assert relationship.target == ArtifactKey(repository_id="urn:raptor:repo:alpha", document_id="DOC-CORE-0002", artifact_id="REQ-CORE-0002")
    assert relationship in store.reverse_typed_relationships(relationship.target)


def test_v2_allows_duplicate_local_ids_across_documents() -> None:
    first, second = _document("DOC-CORE-0001", "REQ-CORE-0001"), _document("DOC-CORE-0002", "REQ-CORE-0001")
    store = SQLiteArtifactStore()
    store.initialize()
    store.put_documents((first, second))
    assert len(store.list_artifact_keys()) == 2
    assert store.get_document(DocumentKey(repository_id="urn:raptor:repo:alpha", document_id="DOC-CORE-0002")) == second
