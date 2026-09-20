from __future__ import annotations

import json
import math
from collections.abc import Iterable
from enum import Enum
from typing import Protocol, cast

from pydantic import JsonValue

from .models import (
    ArtifactKey,
    ArtifactTarget,
    DesignDocument,
    Diagnostic,
    DiagnosticSeverity,
    DocumentKey,
    JsonObject,
    SourceDocument,
    TestPlan,
)


class ReferenceValidationMode(str, Enum):
    STRUCTURAL = "structural"
    DOCUMENT = "document"
    BATCH = "batch"
    STORE = "store"


class ArtifactResolver(Protocol):
    def contains(self, key: ArtifactKey) -> bool: ...


class ReferenceValidationError(ValueError):
    def __init__(
        self,
        diagnostic: Diagnostic,
        *,
        source: ArtifactKey,
        relation: str,
        target: ArtifactKey,
        mode: ReferenceValidationMode,
        document_key: DocumentKey,
        json_pointer: str,
    ) -> None:
        self.diagnostic = diagnostic
        self.source = source
        self.relation = relation
        self.target = target
        self.mode = mode
        self.document_key = document_key
        self.repository_path = diagnostic.repository_path
        self.json_pointer = json_pointer
        super().__init__(f"{diagnostic.code}: {diagnostic.message}")


def _artifact_key(document: SourceDocument, artifact_id: str) -> ArtifactKey:
    return ArtifactKey(
        repository_id=document.provenance.origin.repository_id,
        artifact_id=artifact_id,
    )


def _references(document: SourceDocument) -> Iterable[tuple[ArtifactKey, str, ArtifactKey, str]]:
    for artifact_index, artifact in enumerate(document.artifacts):
        source = _artifact_key(document, artifact.id)
        for index, relationship in enumerate(artifact.relationships):
            if isinstance(relationship.target, ArtifactTarget):
                yield source, relationship.relation.value, relationship.target.key(), f"/artifacts/{artifact_index}/relationships/{index}/target"
        if isinstance(artifact, DesignDocument):
            for component_index, component in enumerate(artifact.components):
                for dependency_index, dependency in enumerate(component.dependencies):
                    yield source, "depends_on", dependency, f"/artifacts/{artifact_index}/components/{component_index}/dependencies/{dependency_index}"
        if isinstance(artifact, TestPlan):
            for case_index, case in enumerate(artifact.test_cases):
                for verifies_index, target in enumerate(case.verifies):
                    yield source, "verifies", target, f"/artifacts/{artifact_index}/test_cases/{case_index}/verifies/{verifies_index}"


def _reference_diagnostic(
    document: SourceDocument,
    source: ArtifactKey,
    relation: str,
    target: ArtifactKey,
) -> Diagnostic:
    origin = document.provenance.origin
    return Diagnostic(
        code="RAPTOR.REFERENCE.UNRESOLVED",
        severity=DiagnosticSeverity.ERROR,
        message=f"unresolved {relation} target {target.repository_id}/{target.artifact_id}",
        repository_id=origin.repository_id,
        document_id=origin.document_id,
        repository_path=document.provenance.materialization.repository_path,
        artifact_key=source,
    )


def _coerce(value: object) -> SourceDocument:
    if isinstance(value, SourceDocument):
        return value
    return SourceDocument.model_validate(value)


def validate_document(
    value: object,
    *,
    reference_mode: ReferenceValidationMode = ReferenceValidationMode.STRUCTURAL,
    resolver: ArtifactResolver | None = None,
) -> SourceDocument:
    reference_mode = ReferenceValidationMode(reference_mode)
    document = _coerce(value)
    if reference_mode is ReferenceValidationMode.STORE and resolver is None:
        raise ValueError("RAPTOR.REFERENCE.RESOLVER_REQUIRED: store mode requires a resolver")
    if reference_mode is ReferenceValidationMode.STRUCTURAL:
        return document
    local = {_artifact_key(document, artifact.id).sort_key() for artifact in document.artifacts}
    for source, relation, target, pointer in _references(document):
        found = target.sort_key() in local
        if reference_mode is ReferenceValidationMode.STORE and not found:
            found = bool(resolver and resolver.contains(target))
        if not found:
            raise ReferenceValidationError(
                _reference_diagnostic(document, source, relation, target),
                source=source,
                relation=relation,
                target=target,
                mode=reference_mode,
                document_key=DocumentKey(
                    repository_id=document.provenance.origin.repository_id,
                    document_id=document.provenance.origin.document_id,
                ),
                json_pointer=pointer,
            )
    return document


def validate_documents(
    values: Iterable[object],
    *,
    reference_mode: ReferenceValidationMode = ReferenceValidationMode.BATCH,
    resolver: ArtifactResolver | None = None,
) -> tuple[SourceDocument, ...]:
    reference_mode = ReferenceValidationMode(reference_mode)
    documents = tuple(_coerce(value) for value in values)
    if reference_mode in {ReferenceValidationMode.STRUCTURAL, ReferenceValidationMode.DOCUMENT}:
        return tuple(
            validate_document(document, reference_mode=reference_mode, resolver=resolver)
            for document in documents
        )
    if reference_mode is ReferenceValidationMode.STORE and resolver is None:
        raise ValueError("RAPTOR.REFERENCE.RESOLVER_REQUIRED: store mode requires a resolver")
    keys: set[tuple[str, str]] = set()
    for document in documents:
        for artifact in document.artifacts:
            key = _artifact_key(document, artifact.id)
            if key.sort_key() in keys:
                raise ValueError(f"RAPTOR.REFERENCE.DUPLICATE: {key.repository_id}/{key.artifact_id}")
            keys.add(key.sort_key())
    for document in documents:
        for source, relation, target, pointer in _references(document):
            found = target.sort_key() in keys or (
                reference_mode is ReferenceValidationMode.STORE
                and bool(resolver and resolver.contains(target))
            )
            if not found:
                raise ReferenceValidationError(
                    _reference_diagnostic(document, source, relation, target),
                    source=source,
                    relation=relation,
                    target=target,
                    mode=reference_mode,
                    document_key=DocumentKey(
                        repository_id=document.provenance.origin.repository_id,
                        document_id=document.provenance.origin.document_id,
                    ),
                    json_pointer=pointer,
                )
    return documents


def _normalize_numbers(value: JsonValue) -> JsonValue:
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("canonical JSON rejects non-finite floats")
        return 0.0 if value == 0.0 else value
    if isinstance(value, list):
        return [_normalize_numbers(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalize_numbers(item) for key, item in value.items()}
    return value


def dump_canonical_json(value: SourceDocument | object) -> str:
    document = _coerce(value)
    payload = cast(JsonObject, document.model_dump(mode="json", exclude_none=True))
    return json.dumps(
        _normalize_numbers(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ) + "\n"


def load_canonical_json(value: str | bytes | bytearray) -> SourceDocument:
    return SourceDocument.model_validate_json(value)
