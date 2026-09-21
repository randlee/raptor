from __future__ import annotations

from copy import deepcopy

import pytest

from raptor_schema import (
    ArtifactKey,
    ReferenceValidationError,
    ReferenceValidationMode,
    validate_document,
    validate_documents,
)


class Resolver:
    def __init__(self, keys: set[tuple[str, str]]) -> None:
        self.keys = keys

    def contains(self, key: ArtifactKey) -> bool:
        return (key.repository_id, key.artifact_id) in self.keys


def test_same_document_resolution(document_dict: dict[str, object]) -> None:
    validate_document(document_dict, reference_mode=ReferenceValidationMode.DOCUMENT)


def test_missing_cross_repository_by_mode(document_dict: dict[str, object]) -> None:
    target = document_dict["artifacts"][1]["relationships"][0]["target"]  # type: ignore[index]
    target["repository_id"] = "urn:raptor:repo:remote"  # type: ignore[index]
    validate_document(document_dict, reference_mode=ReferenceValidationMode.STRUCTURAL)
    for mode in (ReferenceValidationMode.DOCUMENT, ReferenceValidationMode.BATCH):
        with pytest.raises(ReferenceValidationError) as caught:
            if mode is ReferenceValidationMode.DOCUMENT:
                validate_document(document_dict, reference_mode=mode)
            else:
                validate_documents([document_dict], reference_mode=mode)
        diagnostic = caught.value.diagnostic
        assert diagnostic.code == "RAPTOR.REFERENCE.UNRESOLVED"
        assert caught.value.target.repository_id == "urn:raptor:repo:remote"
        assert caught.value.relation == "satisfies"
        assert caught.value.mode is mode
        assert caught.value.json_pointer.startswith("/artifacts/")


def test_store_resolver_and_required(document_dict: dict[str, object]) -> None:
    target = document_dict["artifacts"][1]["relationships"][0]["target"]  # type: ignore[index]
    target["repository_id"] = "urn:raptor:repo:remote"  # type: ignore[index]
    with pytest.raises(ValueError, match="RESOLVER_REQUIRED"):
        validate_documents([document_dict], reference_mode=ReferenceValidationMode.STORE)
    validate_documents(
        [document_dict],
        reference_mode=ReferenceValidationMode.STORE,
        resolver=Resolver({("urn:raptor:repo:remote", "REQ-RAP-001")}),
    )


def test_store_unresolved_reports_complete_context(document_dict: dict[str, object]) -> None:
    target = document_dict["artifacts"][1]["relationships"][0]["target"]  # type: ignore[index]
    target["repository_id"] = "urn:raptor:repo:remote"  # type: ignore[index]
    with pytest.raises(ReferenceValidationError) as caught:
        validate_documents(
            [document_dict],
            reference_mode=ReferenceValidationMode.STORE,
            resolver=Resolver(set()),
        )
    error = caught.value
    diagnostic = error.diagnostic
    assert diagnostic.code == "RAPTOR.REFERENCE.UNRESOLVED"
    assert diagnostic.repository_id == "urn:raptor:repo:raptor"
    assert diagnostic.document_id == "DOC-RAP-001"
    assert diagnostic.repository_path == "docs/requirements.md"
    assert diagnostic.artifact_key == ArtifactKey(
        repository_id="urn:raptor:repo:raptor", artifact_id="NFR-RAP-004"
    )
    assert error.source == diagnostic.artifact_key
    assert error.target == ArtifactKey(
        repository_id="urn:raptor:repo:remote", artifact_id="REQ-RAP-001"
    )
    assert error.mode is ReferenceValidationMode.STORE
    assert error.document_key.repository_id == diagnostic.repository_id
    assert error.document_key.document_id == diagnostic.document_id
    assert error.repository_path == diagnostic.repository_path
    assert error.relation == "satisfies"
    assert error.json_pointer == "/artifacts/1/relationships/0/target"


def test_forward_cyclic_batch_and_duplicate(document_dict: dict[str, object]) -> None:
    left = deepcopy(document_dict)
    left["artifacts"] = [deepcopy(document_dict["artifacts"][0])]  # type: ignore[index]
    left["artifacts"][0]["relationships"] = [{  # type: ignore[index]
        "relation": "depends_on",
        "target": {"target_kind": "artifact", "repository_id": "urn:raptor:repo:remote", "artifact_id": "REQ-RAP-002"},
    }]
    right = deepcopy(left)
    right["provenance"]["origin"]["repository_id"] = "urn:raptor:repo:remote"  # type: ignore[index]
    right["provenance"]["origin"]["document_id"] = "DOC-RAP-002"  # type: ignore[index]
    right["provenance"]["origin"]["initial_repository_path"] = "docs/remote.md"  # type: ignore[index]
    right["provenance"]["materialization"]["repository_path"] = "docs/remote.md"  # type: ignore[index]
    right["artifacts"][0]["id"] = "REQ-RAP-002"  # type: ignore[index]
    right["artifacts"][0]["relationships"][0]["target"] = {  # type: ignore[index]
        "target_kind": "artifact", "repository_id": "urn:raptor:repo:raptor", "artifact_id": "REQ-RAP-001"
    }
    validate_documents([left, right], reference_mode=ReferenceValidationMode.BATCH)
    with pytest.raises(ValueError, match="RAPTOR.REFERENCE.DUPLICATE"):
        validate_documents([left, left], reference_mode=ReferenceValidationMode.BATCH)


def test_same_local_id_in_two_repositories_does_not_collide(document_dict: dict[str, object]) -> None:
    left = deepcopy(document_dict)
    left["artifacts"] = [deepcopy(document_dict["artifacts"][0])]  # type: ignore[index]
    left["artifacts"][0]["relationships"] = []  # type: ignore[index]
    right = deepcopy(left)
    right["provenance"]["origin"]["repository_id"] = "urn:raptor:repo:remote"  # type: ignore[index]
    right["provenance"]["origin"]["document_id"] = "DOC-RAP-001"  # type: ignore[index]
    validate_documents([left, right], reference_mode=ReferenceValidationMode.BATCH)
