from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal
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
    DRAFT = "draft"
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    IMPLEMENTED = "implemented"
    VERIFIED = "verified"
    DEPRECATED = "deprecated"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class DiagnosticSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class RelationshipType(str, Enum):
    DEPENDS_ON = "depends_on"
    SATISFIES = "satisfies"
    IMPLEMENTS = "implements"
    VERIFIES = "verifies"
    SUPERSEDES = "supersedes"
    RELATES_TO = "relates_to"


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DocumentKey(ContractModel):
    repository_id: RepositoryId
    document_id: DocumentId


class ArtifactKey(ContractModel):
    repository_id: RepositoryId
    artifact_id: ArtifactId

    def sort_key(self) -> tuple[str, str]:
        return self.repository_id, self.artifact_id


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


class ArtifactTarget(ContractModel):
    target_kind: Literal["artifact"]
    repository_id: RepositoryId
    artifact_id: ArtifactId

    def key(self) -> ArtifactKey:
        return ArtifactKey(repository_id=self.repository_id, artifact_id=self.artifact_id)


class UriTarget(ContractModel):
    target_kind: Literal["uri"]
    target_uri: str = Field(
        pattern=r"^(?:https?://[^\x00-\x20\x7f/?#]+(?:[/?#][^\x00-\x20\x7f]*)?|urn:[A-Za-z0-9](?:[A-Za-z0-9-]{0,30}[A-Za-z0-9])?:[A-Za-z0-9()+,.:=@;$_!*'%/?#-]+)$"
    )


RelationshipTarget = Annotated[ArtifactTarget | UriTarget, Field(discriminator="target_kind")]


class ArtifactRelationship(ContractModel):
    relation: RelationshipType
    target: RelationshipTarget
    description: NonEmptyText | None = None

    def sort_key(self) -> tuple[str, str, str, str]:
        if isinstance(self.target, ArtifactTarget):
            return (
                self.relation.value,
                self.target.target_kind,
                self.target.repository_id,
                self.target.artifact_id,
            )
        return (self.relation.value, self.target.target_kind, "", self.target.target_uri)


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
    "ArtifactRelationship",
    "ArtifactTarget",
    "ArtifactType",
    "Diagnostic",
    "DiagnosticSeverity",
    "DocumentKey",
    "LifecycleStatus",
    "Priority",
    "RelationshipTarget",
    "RelationshipType",
    "SourceLocation",
    "UriTarget",
]
