from raptor_schema import ArtifactKey, SourceDocument


def test_v2_allows_same_local_artifact_id_in_separate_documents() -> None:
    base = {
        "schema_version": "2.0.0",
        "provenance": {
            "origin": {"repository_id": "urn:raptor:repo:alpha", "document_id": "DOC-CORE-0001", "initial_repository_path": "docs/a.md", "original_content_sha256": "0" * 64, "source_format": "markdown", "parser_profile": "raptor", "parser_profile_version": "2.0.0"},
            "materialization": {"repository_path": "docs/a.md", "content_sha256": "0" * 64, "operation": "imported", "parser_profile": "raptor", "parser_profile_version": "2.0.0"},
        },
        "artifacts": [{"artifact_type": "requirement", "id": "REQ-CORE-0001", "title": "Lossless", "content": "\ntext\n"}],
    }
    first = SourceDocument.model_validate(base)
    second = SourceDocument.model_validate({**base, "provenance": {**base["provenance"], "origin": {**base["provenance"]["origin"], "document_id": "DOC-CORE-0002", "initial_repository_path": "docs/b.md"}, "materialization": {**base["provenance"]["materialization"], "repository_path": "docs/b.md"}}})
    assert ArtifactKey(repository_id="urn:raptor:repo:alpha", document_id=first.provenance.origin.document_id, artifact_id=first.artifacts[0].id) != ArtifactKey(repository_id="urn:raptor:repo:alpha", document_id=second.provenance.origin.document_id, artifact_id=second.artifacts[0].id)
