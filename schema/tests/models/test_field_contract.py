from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from raptor_schema import (
    ArtifactRelationship,
    SourceDocument,
    dump_canonical_json,
    load_canonical_json,
)


def test_all_families_round_trip_and_omission(document: SourceDocument) -> None:
    assert [item.artifact_type.value for item in document.artifacts] == [
        "requirement",
        "non_functional_requirement",
        "architecture_decision",
        "design_document",
        "test_plan",
    ]
    dumped = dump_canonical_json(document)
    assert dumped.endswith("\n") and not dumped.endswith("\n\n")
    assert load_canonical_json(dumped) == document
    payload = json.loads(dumped)
    assert "summary" not in payload["artifacts"][0]
    assert payload["artifacts"][2]["alternatives"]
    assert payload["artifacts"][4]["entry_criteria"] == []


def test_canonical_dump_revalidates_live_mutable_collections(
    document: SourceDocument,
) -> None:
    relationships = document.artifacts[0].relationships
    relationships.extend(
        [
            ArtifactRelationship.model_validate(
                {
                    "relation": "verifies",
                    "target": {
                        "target_kind": "uri",
                        "target_uri": "https://example.test/z",
                    },
                }
            ),
            ArtifactRelationship.model_validate(
                {
                    "relation": "depends_on",
                    "target": {
                        "target_kind": "uri",
                        "target_uri": "https://example.test/a",
                    },
                }
            ),
        ]
    )
    canonical = dump_canonical_json(document)
    relationships.reverse()
    assert dump_canonical_json(document) == canonical
    relationships.append(relationships[0])
    with pytest.raises(ValidationError, match="duplicate artifact relationship"):
        dump_canonical_json(document)


def test_unknown_field_and_bad_version_rejected(document_dict: dict[str, object]) -> None:
    document_dict["surprise"] = True
    with pytest.raises(ValidationError, match="extra_forbidden"):
        SourceDocument.model_validate(document_dict)
    document_dict.pop("surprise")
    document_dict["schema_version"] = "2.0.0"
    with pytest.raises(ValidationError, match="String should match pattern"):
        SourceDocument.model_validate(document_dict)


def test_discriminator_prefix_and_duplicate_rejected(document_dict: dict[str, object]) -> None:
    document_dict["artifacts"][0]["id"] = "NFR-RAP-001"  # type: ignore[index]
    with pytest.raises(ValidationError, match="REQ prefix"):
        SourceDocument.model_validate(document_dict)
    document_dict["artifacts"][0]["id"] = "REQ-RAP-001"  # type: ignore[index]
    document_dict["artifacts"].append(document_dict["artifacts"][0])  # type: ignore[union-attr,index]
    with pytest.raises(ValidationError, match="duplicate artifact"):
        SourceDocument.model_validate(document_dict)


def test_relationship_ordering_duplicate_and_extension_namespace(document_dict: dict[str, object]) -> None:
    artifact = document_dict["artifacts"][0]  # type: ignore[index]
    artifact["relationships"] = [  # type: ignore[index]
        {"relation": "verifies", "target": {"target_kind": "uri", "target_uri": "https://example.test/z"}},
        {"relation": "depends_on", "target": {"target_kind": "uri", "target_uri": "https://example.test/a"}},
    ]
    parsed = SourceDocument.model_validate(document_dict)
    assert [r.relation.value for r in parsed.artifacts[0].relationships] == ["depends_on", "verifies"]
    artifact["relationships"].append(artifact["relationships"][0])  # type: ignore[index,union-attr]
    with pytest.raises(ValidationError, match="duplicate artifact relationship"):
        SourceDocument.model_validate(document_dict)
    artifact["relationships"].pop()  # type: ignore[index,union-attr]
    artifact["extensions"] = {"NotNamespaced": 1}  # type: ignore[index]
    with pytest.raises(ValidationError):
        SourceDocument.model_validate(document_dict)


def test_uri_and_json_extension_constraints(document_dict: dict[str, object]) -> None:
    artifact = document_dict["artifacts"][0]  # type: ignore[index]
    artifact["relationships"][0]["target"]["target_uri"] = "relative"  # type: ignore[index]
    with pytest.raises(ValidationError, match="String should match pattern"):
        SourceDocument.model_validate(document_dict)
    artifact["relationships"][0]["target"]["target_uri"] = "urn:raptor:test"  # type: ignore[index]
    artifact["extensions"] = {"raptor.number": float("nan")}  # type: ignore[index]
    with pytest.raises(ValidationError, match="finite"):
        SourceDocument.model_validate(document_dict)
