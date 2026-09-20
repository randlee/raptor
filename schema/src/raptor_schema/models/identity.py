from __future__ import annotations

from pydantic import Field, TypeAdapter, model_validator

from .base import (
    DOCUMENT_ID_RE,
    ContractModel,
    DocumentId,
    RepositoryId,
    RepositoryPath,
    SchemaVersion,
)

IDENTITY_MISSING = "RAPTOR.IDENTITY.MISSING"
IDENTITY_REPOSITORY_CONFLICT = "RAPTOR.IDENTITY.REPOSITORY_CONFLICT"
IDENTITY_DOCUMENT_CONFLICT = "RAPTOR.IDENTITY.DOCUMENT_CONFLICT"
IDENTITY_PATH_CONFLICT = "RAPTOR.IDENTITY.PATH_CONFLICT"
IDENTITY_REUSE = "RAPTOR.IDENTITY.REUSE"


class IdentityDocument(ContractModel):
    path: RepositoryPath


class IdentityManifest(ContractModel):
    identity_version: SchemaVersion
    repository_id: RepositoryId
    documents: dict[DocumentId, IdentityDocument] = Field(
        json_schema_extra={"propertyNames": {"pattern": DOCUMENT_ID_RE}}
    )

    @model_validator(mode="after")
    def unique_paths(self) -> "IdentityManifest":
        paths = [document.path for document in self.documents.values()]
        if len(paths) != len(set(paths)):
            raise ValueError(f"{IDENTITY_PATH_CONFLICT}: document paths must be unique")
        return self


class IdentityConflict(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


def validate_identity_registration(
    manifest: IdentityManifest | None,
    *,
    repository_id: RepositoryId,
    document_id: DocumentId,
    path: RepositoryPath,
    registered_repository_id: RepositoryId | None = None,
) -> IdentityManifest:
    """Validate one registration without reading or mutating a filesystem."""
    repository_id = TypeAdapter(RepositoryId).validate_python(repository_id)
    document_id = TypeAdapter(DocumentId).validate_python(document_id)
    path = TypeAdapter(RepositoryPath).validate_python(path)
    if registered_repository_id is not None:
        registered_repository_id = TypeAdapter(RepositoryId).validate_python(
            registered_repository_id
        )
    if manifest is None:
        raise IdentityConflict(IDENTITY_MISSING, "identity manifest is required")
    if manifest.repository_id != repository_id:
        raise IdentityConflict(
            IDENTITY_REPOSITORY_CONFLICT, "repository_id is immutable once registered"
        )
    if registered_repository_id is not None and registered_repository_id != repository_id:
        raise IdentityConflict(IDENTITY_REUSE, "identity is already registered to another repository")
    current = manifest.documents.get(document_id)
    if current is not None and current.path != path:
        raise IdentityConflict(
            IDENTITY_DOCUMENT_CONFLICT, "document_id is already bound to a different path"
        )
    if any(key != document_id and document.path == path for key, document in manifest.documents.items()):
        raise IdentityConflict(IDENTITY_PATH_CONFLICT, "path is already bound to another document_id")
    if current is not None:
        return manifest
    return manifest.model_copy(
        update={"documents": {**manifest.documents, document_id: IdentityDocument(path=path)}}
    )


__all__ = [
    "IDENTITY_DOCUMENT_CONFLICT",
    "IDENTITY_MISSING",
    "IDENTITY_PATH_CONFLICT",
    "IDENTITY_REPOSITORY_CONFLICT",
    "IDENTITY_REUSE",
    "IdentityConflict",
    "IdentityDocument",
    "IdentityManifest",
    "validate_identity_registration",
]
