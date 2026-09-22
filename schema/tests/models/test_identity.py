from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from raptor_schema import (
    IDENTITY_DOCUMENT_CONFLICT,
    IDENTITY_MISSING,
    IDENTITY_PATH_CONFLICT,
    IDENTITY_REPOSITORY_CONFLICT,
    IDENTITY_REUSE,
    IdentityConflict,
    IdentityManifest,
    validate_identity_registration,
)

ROOT = Path(__file__).parents[3]


def manifest() -> IdentityManifest:
    return IdentityManifest.model_validate_json((ROOT / ".raptor/identity.json").read_text())


def test_identity_manifest_dogfood_and_canonical_shape() -> None:
    value = manifest()
    assert value.repository_id == "urn:raptor:repo:raptor"
    assert len(value.documents) == 8
    canonical = json.dumps(value.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    assert canonical.index("DOC-RAP-001") < canonical.index("DOC-RAP-007")


def test_identity_is_independent_of_clone_root(tmp_path: Path) -> None:
    first = manifest()
    clone = tmp_path / "renamed-clone"
    clone.mkdir()
    assert IdentityManifest.model_validate(first.model_dump()) == first


def test_registration_idempotence_and_conflicts() -> None:
    value = manifest()
    assert validate_identity_registration(
        value,
        repository_id=value.repository_id,
        document_id="DOC-RAP-001",
        path="docs/requirements.md",
    ) is value
    added = validate_identity_registration(
        value,
        repository_id=value.repository_id,
        document_id="DOC-RAP-099",
        path="docs/new.md",
    )
    assert added.documents["DOC-RAP-099"].path == "docs/new.md"
    with pytest.raises(TypeError):
        added.documents["DOC-RAP-100"] = added.documents["DOC-RAP-099"]  # type: ignore[index]
    cases = [
        (IDENTITY_MISSING, dict(manifest=None, repository_id="urn:raptor:repo:raptor", document_id="DOC-RAP-001", path="docs/requirements.md")),
        (IDENTITY_REPOSITORY_CONFLICT, dict(manifest=value, repository_id="urn:raptor:repo:other", document_id="DOC-RAP-001", path="docs/requirements.md")),
        (IDENTITY_DOCUMENT_CONFLICT, dict(manifest=value, repository_id=value.repository_id, document_id="DOC-RAP-001", path="docs/moved.md")),
        (IDENTITY_PATH_CONFLICT, dict(manifest=value, repository_id=value.repository_id, document_id="DOC-RAP-099", path="docs/requirements.md")),
        (IDENTITY_REUSE, dict(manifest=value, repository_id=value.repository_id, document_id="DOC-RAP-001", path="docs/requirements.md", registered_repository_id="urn:raptor:repo:other")),
    ]
    for code, kwargs in cases:
        with pytest.raises(IdentityConflict) as caught:
            validate_identity_registration(**kwargs)
        assert caught.value.code == code


def test_manifest_duplicate_path_rejected() -> None:
    value = manifest().model_dump(mode="json")
    value["documents"]["DOC-RAP-099"] = {"path": "docs/requirements.md"}
    with pytest.raises(ValidationError, match="PATH_CONFLICT"):
        IdentityManifest.model_validate(value)


def test_identity_manifest_and_documents_are_defensively_immutable() -> None:
    value = manifest()
    with pytest.raises(ValidationError, match="frozen"):
        value.repository_id = "urn:raptor:repo:other"
    with pytest.raises(TypeError):
        value.documents["DOC-RAP-099"] = value.documents["DOC-RAP-001"]  # type: ignore[index]
    with pytest.raises(ValidationError, match="frozen"):
        value.documents["DOC-RAP-001"].path = "docs/other.md"

    copied = value.model_copy(
        update={
            "documents": {
                **value.documents,
                "DOC-RAP-099": {"path": "docs/new.md"},
            }
        }
    )
    assert "DOC-RAP-099" not in value.documents
    assert copied.documents["DOC-RAP-099"].path == "docs/new.md"
    with pytest.raises(TypeError):
        copied.documents["DOC-RAP-100"] = copied.documents["DOC-RAP-099"]  # type: ignore[index]


def test_identity_manifest_snapshots_caller_documents() -> None:
    documents = {"DOC-RAP-099": {"path": "docs/new.md"}}
    value = IdentityManifest.model_validate(
        {
            "identity_version": "1.0.0",
            "repository_id": "urn:raptor:repo:raptor",
            "documents": documents,
        }
    )
    documents.clear()
    assert "DOC-RAP-099" in value.documents
