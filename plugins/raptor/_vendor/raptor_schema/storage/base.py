from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Protocol

from ..canonical import ArtifactResolver, ReferenceValidationError, dump_canonical_json
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


class StorageError(ValueError):
    """Stable, dialect-neutral persistence contract failure."""


@dataclass(frozen=True)
class StoreConformanceCorpus:
    """Documents needed to exercise the complete adapter contract."""

    round_trip: tuple[SourceDocument, ...]
    acyclic_batch: tuple[SourceDocument, ...]
    cyclic_batch: tuple[SourceDocument, ...]
    overlay_target: SourceDocument
    overlay_source: SourceDocument
    rollback_valid: SourceDocument
    rollback_invalid: SourceDocument
    replacement_initial: SourceDocument
    replacement: SourceDocument
    inbound_target: SourceDocument
    inbound_source: SourceDocument
    inbound_replacement: SourceDocument
    invalid_initial: SourceDocument
    invalid_replacement: SourceDocument
    path_conflict: tuple[SourceDocument, SourceDocument]
    artifact_conflict: tuple[SourceDocument, SourceDocument]


def _rendered_replacement(document: SourceDocument) -> SourceDocument:
    replacement = document.model_copy(deep=True)
    replacement.artifacts[0].title += " (replacement)"
    current = document.provenance.materialization
    replacement.provenance.materialization = current.model_copy(
        update={
            "content_sha256": hashlib.sha256(
                dump_canonical_json(replacement).encode()
            ).hexdigest(),
            "operation": "rendered",
            "parent_content_sha256": current.content_sha256,
            "template_set": "raptor_conformance",
            "template_version": "1.0.0",
        }
    )
    return replacement


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
        recovered = store.get_document(document_key(document))
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

    for document in expected:
        replacement = _rendered_replacement(document)
        store.put_document(replacement)
        recovered = store.get_document(document_key(replacement))
        if dump_canonical_json(recovered) != dump_canonical_json(replacement):
            raise AssertionError("valid rendered replacement did not round-trip")
        store.delete_document(document_key(replacement))
        try:
            store.get_document(document_key(replacement))
        except KeyError:
            pass
        else:
            raise AssertionError("deleted document remains readable")


def assert_store_factory_conformance(
    factory: Callable[[], ArtifactStore], corpus: StoreConformanceCorpus
) -> None:
    """Run each adapter behavior against an isolated, freshly initialized store."""

    assert_store_conformance(factory(), corpus.round_trip)

    for documents in (corpus.acyclic_batch, corpus.cyclic_batch):
        store = factory()
        store.initialize()
        store.put_documents(documents)
        for document in documents:
            if dump_canonical_json(
                store.get_document(document_key(document))
            ) != dump_canonical_json(document):
                raise AssertionError("batch document did not round-trip")

    store = factory()
    store.initialize()
    store.put_document(corpus.overlay_target)
    store.put_document(corpus.overlay_source)

    store = factory()
    store.initialize()
    try:
        store.put_documents((corpus.rollback_valid, corpus.rollback_invalid))
    except ReferenceValidationError:
        pass
    else:
        raise AssertionError("invalid batch did not fail")
    if store.contains(_first_key(corpus.rollback_valid)):
        raise AssertionError("failed batch was not rolled back")

    store = factory()
    store.initialize()
    store.put_document(corpus.replacement_initial)
    store.put_document(corpus.replacement)
    if dump_canonical_json(
        store.get_document(document_key(corpus.replacement))
    ) != dump_canonical_json(corpus.replacement):
        raise AssertionError("replacement did not round-trip")

    store = factory()
    store.initialize()
    store.put_documents((corpus.inbound_target, corpus.inbound_source))
    inbound_conflicts: tuple[Callable[[], None], ...] = (
        lambda: store.put_document(corpus.inbound_replacement),
        lambda: store.delete_document(document_key(corpus.inbound_target)),
    )
    for operation in inbound_conflicts:
        try:
            operation()
        except StorageError:
            pass
        else:
            raise AssertionError("inbound reference conflict was accepted")
    store.delete_document(document_key(corpus.inbound_source))
    store.delete_document(document_key(corpus.inbound_target))

    store = factory()
    store.initialize()
    store.put_document(corpus.invalid_initial)
    try:
        store.put_document(corpus.invalid_replacement)
    except StorageError:
        pass
    else:
        raise AssertionError("invalid provenance transition was accepted")

    store = factory()
    store.initialize()
    try:
        store.put_documents(corpus.path_conflict)
    except StorageError:
        pass
    else:
        raise AssertionError("path conflict was accepted")
    if store.list_artifact_keys():
        raise AssertionError("path conflict was not rolled back")

    store = factory()
    store.initialize()
    store.put_document(corpus.artifact_conflict[0])
    try:
        store.put_document(corpus.artifact_conflict[1])
    except StorageError:
        pass
    else:
        raise AssertionError("artifact ownership conflict was accepted")
    if dump_canonical_json(
        store.get_document(document_key(corpus.artifact_conflict[0]))
    ) != dump_canonical_json(corpus.artifact_conflict[0]):
        raise AssertionError("artifact conflict did not roll back")


def _first_key(document: SourceDocument) -> ArtifactKey:
    origin = document.provenance.origin
    return ArtifactKey(
        repository_id=origin.repository_id,
        artifact_id=document.artifacts[0].id,
    )


def document_key(document: SourceDocument) -> DocumentKey:
    origin = document.provenance.origin
    return DocumentKey(
        repository_id=origin.repository_id, document_id=origin.document_id
    )


__all__ = [
    "ArtifactStore",
    "StorageError",
    "StoreConformanceCorpus",
    "assert_store_conformance",
    "assert_store_factory_conformance",
    "document_key",
]
