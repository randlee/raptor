"""Strict-mypy probes for public profile and persistence protocols."""

from __future__ import annotations

from typing import assert_type

from raptor_schema import (
    ArtifactSnapshot,
    ArtifactStore,
    ComparableDocument,
    Diagnostic,
    JsonObject,
    ParsedDocument,
    SourceDocument,
    SourceInput,
    SourceProfile,
    SQLiteArtifactStore,
)


class ConsumerProfile:
    profile_id = "consumer"
    profile_version = "1.0.0"

    def parse(self, source: SourceInput) -> ParsedDocument:
        return ParsedDocument(source=source, frontmatter={}, sections=())

    def validate(self, parsed: ParsedDocument) -> list[Diagnostic]:
        return []

    def canonicalize(self, parsed: ParsedDocument) -> SourceDocument:
        raise NotImplementedError

    def project_render_input(self, document: SourceDocument) -> JsonObject:
        return {"schema_version": document.schema_version}

    def normalize(self, document: SourceDocument) -> ComparableDocument:
        return ComparableDocument(
            schema_version=document.schema_version,
            origin=document.provenance.origin,
            artifacts=tuple(ArtifactSnapshot.from_artifact(item) for item in document.artifacts),
        )


consumer_profile: SourceProfile = ConsumerProfile()
assert_type(consumer_profile, SourceProfile)

artifact_store: ArtifactStore = SQLiteArtifactStore()
assert_type(artifact_store, ArtifactStore)
