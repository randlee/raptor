from __future__ import annotations

import hashlib
from typing import Literal

from pydantic import model_validator

from .base import ContractModel, DocumentId, ProfileId, ProfileVersion, RepositoryId, RepositoryPath, Sha256


class OriginProvenance(ContractModel):
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
    template_set: str | None = None
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


class SourceProvenance(ContractModel):
    origin: OriginProvenance
    materialization: MaterializationProvenance

    @model_validator(mode="after")
    def first_import_consistency(self) -> "SourceProvenance":
        if self.materialization.operation == "imported":
            if self.origin.initial_repository_path != self.materialization.repository_path:
                raise ValueError("first import origin and materialization paths must match")
            if self.origin.original_content_sha256 != self.materialization.content_sha256:
                raise ValueError("first import origin and materialization hashes must match")
        return self


def create_rendered_provenance(
    previous: SourceProvenance,
    *,
    repository_path: RepositoryPath,
    content: bytes,
    parser_profile: ProfileId,
    parser_profile_version: ProfileVersion,
    template_set: str,
    template_version: ProfileVersion,
) -> SourceProvenance:
    """Build a validated render transition without performing filesystem I/O."""
    return SourceProvenance(
        origin=previous.origin,
        materialization=MaterializationProvenance(
            repository_path=repository_path,
            content_sha256=hashlib.sha256(content).hexdigest(),
            operation="rendered",
            parent_content_sha256=previous.materialization.content_sha256,
            parser_profile=parser_profile,
            parser_profile_version=parser_profile_version,
            template_set=template_set,
            template_version=template_version,
        ),
    )


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
