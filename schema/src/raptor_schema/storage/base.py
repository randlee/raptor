from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from ..canonical import ArtifactResolver, dump_canonical_json
from ..models import ArtifactKey, DocumentKey, RepositoryId, SourceDocument


class ArtifactStore(ArtifactResolver, Protocol):
    def initialize(self) -> None: ...
    def contains(self, key: ArtifactKey) -> bool: ...
    def put_document(self, document: SourceDocument) -> None: ...
    def put_documents(self, documents: Iterable[SourceDocument]) -> None: ...
    def get_document(self, key: DocumentKey) -> SourceDocument: ...
    def delete_document(self, key: DocumentKey) -> None: ...
    def list_artifact_keys(
        self,
        *,
        repository_id: RepositoryId | None = None,
        artifact_type: str | None = None,
    ) -> list[ArtifactKey]: ...


def assert_store_conformance(
    store: ArtifactStore, documents: Iterable[SourceDocument]
) -> None:
    """Exercise the reusable lossless persistence contract for validated models."""
    expected = tuple(documents)
    store.initialize()
    store.put_documents(expected)
    expected_keys: list[ArtifactKey] = []
    for document in expected:
        origin = document.provenance.origin
        key = DocumentKey(
            repository_id=origin.repository_id, document_id=origin.document_id
        )
        recovered = store.get_document(key)
        if dump_canonical_json(recovered) != dump_canonical_json(document):
            raise AssertionError(f"document did not round-trip: {origin.document_id}")
        expected_keys.extend(
            ArtifactKey(repository_id=origin.repository_id, artifact_id=artifact.id)
            for artifact in document.artifacts
        )
    store.put_documents(expected)
    actual = store.list_artifact_keys()
    if actual != sorted(expected_keys, key=ArtifactKey.sort_key):
        raise AssertionError("artifact key listing disagrees with stored documents")
    if not all(store.contains(key) for key in expected_keys):
        raise AssertionError("stored artifact is missing from resolver")


__all__ = ["ArtifactStore", "assert_store_conformance"]
