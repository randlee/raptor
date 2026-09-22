from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from .artifacts import Artifact
from .base import ContractModel
from .provenance import SourceProvenance


class DocumentSegment(ContractModel):
    kind: Literal["text", "artifact"]
    content: str = ""
    artifact_index: int | None = Field(default=None, ge=0)


class SourceDocument(ContractModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    provenance: SourceProvenance = Field(frozen=True)
    title: str | None = None
    document_metadata: dict[str, Any] = Field(default_factory=dict)
    non_item_segments: list[DocumentSegment] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(min_length=1)

    @property
    def segments(self) -> list[DocumentSegment]:
        return self.non_item_segments


__all__ = ["DocumentSegment", "SourceDocument"]
