from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator

from .base import (
    ArtifactId,
    ContractModel,
    Title,
)
from .common import (
    ArtifactType,
    LifecycleStatus,
    SourceLocation,
)
class Relationship(ContractModel):
    relation_type: str
    target_token: str
    context: str
    target_repository_id: str | None = None
    target_document_id: str | None = None
    target_artifact_id: str | None = None


class Subsection(ContractModel):
    title: str
    level: int = Field(ge=3, le=6)
    markdown: str
    ordinal: int = Field(ge=0)
    source: dict[str, Any] = Field(default_factory=dict)


class Artifact(ContractModel):
    """The v2 generic index record; family-specific payloads are intentionally absent."""

    artifact_type: ArtifactType
    id: ArtifactId
    title: Title
    status: LifecycleStatus | None = None
    domain: str | None = None
    source: dict[str, Any] = Field(default_factory=dict)
    content: str = ""
    relationships: list[Relationship] = Field(default_factory=list)
    subsections: list[Subsection] = Field(default_factory=list)
    source_location: SourceLocation | None = None

    @field_validator("relationships")
    @classmethod
    def preserve_relationship_order(cls, value: list[Relationship]) -> list[Relationship]:
        return value


__all__ = [
    "Artifact",
    "Relationship",
    "Subsection",
]
