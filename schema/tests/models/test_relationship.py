from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from raptor_schema import ArtifactRelationship, SourceDocument


@pytest.mark.parametrize(
    "target",
    [
        {
            "target_kind": "artifact",
            "repository_id": "urn:raptor:repo:raptor",
            "artifact_id": "REQ-RAP-001",
        },
        {"target_kind": "uri", "target_uri": "https://example.test/requirement"},
        {"target_kind": "uri", "target_uri": "http://example.test/requirement"},
        {"target_kind": "uri", "target_uri": "urn:raptor:requirement:1"},
    ],
)
def test_relationship_target_positive_matrix(target: dict[str, object]) -> None:
    relation = ArtifactRelationship(
        relation="depends_on", target=target, description="a typed dependency"
    )
    assert relation.target.target_kind in {"artifact", "uri"}


@pytest.mark.parametrize(
    "target",
    [
        {},
        {"target_kind": "missing"},
        {"target_kind": "uri", "target_uri": "relative/path"},
        {"target_kind": "uri", "target_uri": "https:///missing-host"},
        {"target_kind": "uri", "target_uri": "file:///tmp/source"},
        {"target_kind": "artifact", "repository_id": "bad", "artifact_id": "REQ-RAP-001"},
        {"target_kind": "artifact", "repository_id": "urn:raptor:repo:raptor", "artifact_id": "BAD-001"},
        {
            "target_kind": "artifact",
            "repository_id": "urn:raptor:repo:raptor",
            "artifact_id": "REQ-RAP-001",
            "target_uri": "urn:also:present",
        },
    ],
)
def test_relationship_target_negative_matrix(target: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ArtifactRelationship(relation="depends_on", target=target)


@pytest.mark.parametrize(
    ("field", "value"),
    [("relation", "owns"), ("description", "   "), ("unknown", True)],
)
def test_relationship_envelope_negative_matrix(field: str, value: object) -> None:
    candidate: dict[str, object] = {
        "relation": "depends_on",
        "target": {"target_kind": "uri", "target_uri": "urn:raptor:test"},
    }
    candidate[field] = value
    with pytest.raises(ValidationError):
        ArtifactRelationship.model_validate(candidate)


def test_relationship_duplicates_rejected_after_canonical_sort(
    document_dict: dict[str, object],
) -> None:
    candidate = deepcopy(document_dict)
    relationships = candidate["artifacts"][0]["relationships"]  # type: ignore[index]
    relationships.append(deepcopy(relationships[0]))  # type: ignore[union-attr,index]
    with pytest.raises(ValidationError, match="duplicate artifact relationship"):
        SourceDocument.model_validate(candidate)
