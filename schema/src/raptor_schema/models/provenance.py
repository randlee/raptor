from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict, Field, GetJsonSchemaHandler, model_validator
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema

from .base import ContractModel, DocumentId, NonEmptyText, ProfileId, ProfileVersion, RepositoryId, RepositoryPath, Sha256


class OriginProvenance(ContractModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True, frozen=True)

    repository_id: RepositoryId
    document_id: DocumentId
    initial_repository_path: RepositoryPath
    original_content_sha256: Sha256
    source_format: Literal["markdown"]
    parser_profile: ProfileId
    parser_profile_version: ProfileVersion


class MaterializationProvenance(ContractModel):
    repository_path: RepositoryPath
    content_sha256: Sha256
    operation: Literal["imported", "rendered"]
    parent_content_sha256: Sha256 | None = None
    parser_profile: ProfileId
    parser_profile_version: ProfileVersion
    template_set: NonEmptyText | None = None
    template_version: ProfileVersion | None = None

    @model_validator(mode="after")
    def operation_fields(self) -> "MaterializationProvenance":
        if self.operation == "imported":
            if any(
                value is not None
                for value in (
                    self.parent_content_sha256,
                    self.template_set,
                    self.template_version,
                )
            ):
                raise ValueError("imported materialization omits parent and template fields")
        else:
            if self.parent_content_sha256 is None:
                raise ValueError("rendered materialization requires parent_content_sha256")
            if not self.template_set or self.template_version is None:
                raise ValueError("rendered materialization requires template identity")
        return self

    @classmethod
    def __get_pydantic_json_schema__(
        cls, schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        result = handler(schema)
        result["allOf"] = [
            {
                "if": {"properties": {"operation": {"const": "imported"}}},
                "then": {
                    "properties": {
                        "parent_content_sha256": {"type": "null"},
                        "template_set": {"type": "null"},
                        "template_version": {"type": "null"},
                    }
                },
            },
            {
                "if": {"properties": {"operation": {"const": "rendered"}}},
                "then": {
                    "required": ["parent_content_sha256", "template_set", "template_version"],
                    "properties": {
                        "parent_content_sha256": {"type": "string"},
                        "template_set": {"type": "string", "minLength": 1, "pattern": r"\S"},
                        "template_version": {"type": "string"},
                    },
                },
            },
        ]
        return result


class SourceProvenance(ContractModel):
    origin: OriginProvenance = Field(frozen=True)
    materialization: MaterializationProvenance

    @model_validator(mode="after")
    def first_import_consistency(self) -> "SourceProvenance":
        if self.materialization.operation == "imported":
            if self.origin.initial_repository_path != self.materialization.repository_path:
                raise ValueError("first import origin and materialization paths must match")
            if self.origin.original_content_sha256 != self.materialization.content_sha256:
                raise ValueError("first import origin and materialization hashes must match")
        return self


def validate_provenance_transition(
    previous: SourceProvenance, current: SourceProvenance
) -> SourceProvenance:
    if current.origin != previous.origin:
        raise ValueError("RAPTOR.PROVENANCE.ORIGIN_REWRITE: origin is immutable")
    if current.materialization.operation != "rendered":
        raise ValueError("RAPTOR.PROVENANCE.OPERATION: transition must be rendered")
    if current.materialization.parent_content_sha256 != previous.materialization.content_sha256:
        raise ValueError("RAPTOR.PROVENANCE.PARENT_HASH: parent hash does not match prior materialization")
    return current


__all__ = [
    "MaterializationProvenance",
    "OriginProvenance",
    "SourceProvenance",
    "validate_provenance_transition",
]
