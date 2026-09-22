from __future__ import annotations

from enum import Enum
from typing import Annotated
from pydantic import ConfigDict, Field, GetJsonSchemaHandler, StrictInt, model_validator
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema

from .base import (
    ArtifactId,
    ContractModel,
    DiagnosticCode,
    DocumentId,
    NonEmptyText,
    RepositoryId,
    RepositoryPath,
)


class ArtifactType(str, Enum):
    REQUIREMENT = "requirement"
    NON_FUNCTIONAL_REQUIREMENT = "non_functional_requirement"
    ARCHITECTURE_DECISION = "architecture_decision"
    DESIGN_DOCUMENT = "design_document"
    TEST_PLAN = "test_plan"


class LifecycleStatus(str, Enum):
    DRAFT = "Draft"
    PROPOSED = "Proposed"
    ACTIVE = "Active"
    APPROVED = "Approved"
    DEPRECATED = "Deprecated"
    SUPERSEDED = "Superseded"


class DiagnosticSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class DocumentKey(ContractModel):
    repository_id: RepositoryId
    document_id: DocumentId


class ArtifactKey(ContractModel):
    repository_id: RepositoryId
    document_id: DocumentId
    artifact_id: ArtifactId

    def sort_key(self) -> tuple[str, str, str]:
        return self.repository_id, self.document_id, self.artifact_id


class SourceLocation(ContractModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True, frozen=True)

    start_line: StrictInt = Field(ge=1)
    start_column: StrictInt = Field(ge=1)
    end_line: StrictInt | None = Field(default=None, ge=1)
    end_column: StrictInt | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_end(self) -> "SourceLocation":
        if (self.end_line is None) != (self.end_column is None):
            raise ValueError("end_line and end_column must be provided together")
        if self.end_line is not None and (self.end_line, self.end_column) < (
            self.start_line,
            self.start_column,
        ):
            raise ValueError("end position may not precede start position")
        return self

    @classmethod
    def __get_pydantic_json_schema__(
        cls, schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        result = handler(schema)
        result["allOf"] = [
            {"if": {"required": ["end_line"]}, "then": {"required": ["end_column"]}},
            {"if": {"required": ["end_column"]}, "then": {"required": ["end_line"]}},
        ]
        return result


class Diagnostic(ContractModel):
    code: DiagnosticCode
    severity: DiagnosticSeverity
    message: NonEmptyText
    repository_id: RepositoryId
    document_id: DocumentId
    repository_path: RepositoryPath
    location: SourceLocation | None = None
    artifact_key: ArtifactKey | None = None


__all__ = [
    "ArtifactKey",
    "ArtifactType",
    "Diagnostic",
    "DiagnosticSeverity",
    "DocumentKey",
    "LifecycleStatus",
    "SourceLocation",
]
