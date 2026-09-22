from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .base import (
    ContractModel,
    DocumentId,
    NonEmptyText,
    RepositoryId,
    RepositoryPath,
    SchemaVersion,
    Sha256,
)
from .config import ProfileSelection, SourceName


class IngressDiagnostic(ContractModel):
    code: NonEmptyText
    message: NonEmptyText


class IngressReportEntry(ContractModel):
    repository_path: RepositoryPath
    outcome: Literal["imported", "diagnosed"]
    document_id: DocumentId | None = None
    route: SourceName | None = None
    profile: ProfileSelection | None = None
    canonical_digest: Sha256 | None = None
    sqlite_outcome: Literal["persisted", "validated", "not_attempted"]
    field_count: int | None = Field(default=None, ge=0)
    relationship_count: int | None = Field(default=None, ge=0)
    origin_digest: Sha256 | None = None
    materialization_digest: Sha256 | None = None
    typed_relationship_count: int | None = Field(default=None, ge=0)
    uri_relationship_count: int | None = Field(default=None, ge=0)
    diagnostic: IngressDiagnostic | None = None

    @model_validator(mode="after")
    def terminal_outcome_details(self) -> "IngressReportEntry":
        required_for_import = (
            self.document_id,
            self.route,
            self.profile,
            self.canonical_digest,
            self.field_count,
            self.relationship_count,
            self.origin_digest,
            self.materialization_digest,
        )
        if self.outcome == "imported":
            if any(value is None for value in required_for_import):
                raise ValueError("imported entry requires canonical ingress details")
            if self.diagnostic is not None:
                raise ValueError("imported entry may not carry a diagnostic")
        elif self.diagnostic is None:
            raise ValueError("diagnosed entry requires a diagnostic")
        return self


class IngressReport(ContractModel):
    report_version: SchemaVersion
    repository_id: RepositoryId
    config_path: RepositoryPath
    database_path: RepositoryPath
    entries: tuple[IngressReportEntry, ...]

    @model_validator(mode="after")
    def entries_are_ordered_and_unique(self) -> "IngressReport":
        paths = [entry.repository_path for entry in self.entries]
        if paths != sorted(paths) or len(paths) != len(set(paths)):
            raise ValueError("report entries must have unique sorted repository paths")
        return self


__all__ = ["IngressDiagnostic", "IngressReport", "IngressReportEntry"]
