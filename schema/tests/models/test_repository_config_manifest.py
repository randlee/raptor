from __future__ import annotations

import pytest
from pydantic import ValidationError

from raptor_schema import (
    IdentityManifest,
    RepositoryConfigManifest,
    validate_repository_manifest_identity,
)


def manifest(repository_id: str = "urn:raptor:repo:raptor") -> RepositoryConfigManifest:
    return RepositoryConfigManifest.model_validate(
        {
            "schema_version": "1.0.0",
            "repository_id": repository_id,
            "files": {
                "scan": "sources.toml",
                "routing": "routing.toml",
                "identity": "identity.json",
            },
        }
    )


def identity(repository_id: str = "urn:raptor:repo:raptor") -> IdentityManifest:
    return IdentityManifest.model_validate(
        {"identity_version": "1.0.0", "repository_id": repository_id, "documents": {}}
    )


def test_manifest_and_identity_repository_ids_must_match() -> None:
    validate_repository_manifest_identity(manifest(), identity())

    with pytest.raises(ValueError, match="REPOSITORY_ID"):
        validate_repository_manifest_identity(
            manifest(), identity("urn:raptor:repo:different")
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("scan", "../sources.toml"),
        ("scan", "/sources.toml"),
        ("scan", ".raptor/sources.toml"),
        ("scan", "sources.json"),
        ("routing", "routing.json"),
        ("identity", "identity.toml"),
        ("identity", "nested\\identity.json"),
    ],
)
def test_manifest_rejects_escaping_or_wrongly_typed_paths(field: str, value: str) -> None:
    payload = manifest().model_dump(mode="python")
    payload["files"][field] = value  # type: ignore[index]

    with pytest.raises(ValidationError):
        RepositoryConfigManifest.model_validate(payload)


def test_manifest_paths_must_be_distinct_and_explicit() -> None:
    payload = manifest().model_dump(mode="python")
    payload["files"]["routing"] = "sources.toml"  # type: ignore[index]
    with pytest.raises(ValidationError, match="must be unique"):
        RepositoryConfigManifest.model_validate(payload)

    del payload["files"]["identity"]  # type: ignore[index]
    with pytest.raises(ValidationError):
        RepositoryConfigManifest.model_validate(payload)
