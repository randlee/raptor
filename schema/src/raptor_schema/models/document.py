from __future__ import annotations

from pydantic import Field, model_validator

from .artifacts import Artifact
from .base import ContractModel, SchemaVersion
from .provenance import SourceProvenance


class SourceDocument(ContractModel):
    schema_version: SchemaVersion
    provenance: SourceProvenance
    artifacts: list[Artifact] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_local_artifact_ids(self) -> "SourceDocument":
        ids = [artifact.id for artifact in self.artifacts]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate artifact key in source document")
        return self


__all__ = ["SourceDocument"]
