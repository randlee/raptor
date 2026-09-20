from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import jsonschema
import pytest

from pydantic import ValidationError

from raptor_schema import IdentityManifest, SourceDocument
from raptor_schema.generate import generate_json_schemas
from raptor_schema.models import Measurement

ROOT = Path(__file__).parents[3]
SCHEMAS = ROOT / "schema/json/v1"


def test_checked_in_schemas_have_no_drift() -> None:
    generate_json_schemas(SCHEMAS, check=True)


def test_source_document_schema_matches_positive_case(document_dict: dict[str, object]) -> None:
    schema = json.loads((SCHEMAS / "source-document.schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(document_dict, schema)
    SourceDocument.model_validate(document_dict)


@pytest.mark.parametrize(
    ("comparator", "target"),
    [("lt", "slow"), ("range", [1, 2, 3]), ("range", [1, 2.5])],
)
def test_measurement_schema_rejects_expressible_cases(
    document_dict: dict[str, object], comparator: str, target: object
) -> None:
    schema = json.loads((SCHEMAS / "source-document.schema.json").read_text())
    measurement = document_dict["artifacts"][1]["measurement"]  # type: ignore[index]
    measurement.update({"comparator": comparator, "target": target})  # type: ignore[union-attr]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(document_dict, schema)


def test_identity_schema_accepts_committed_manifest() -> None:
    schema = json.loads((SCHEMAS / "identity-manifest.schema.json").read_text())
    manifest = json.loads((ROOT / ".raptor/identity.json").read_text())
    jsonschema.validate(manifest, schema)


def test_measurement_shared_comparator_type_unit_matrix(
    measurement_cases: tuple[object, ...],
) -> None:
    schema = Measurement.model_json_schema()
    for case in measurement_cases:
        instance = {
            "name": "threshold",
            "comparator": case.comparator,  # type: ignore[attr-defined]
            "target": case.target,  # type: ignore[attr-defined]
            "unit": case.unit,  # type: ignore[attr-defined]
        }
        errors = list(jsonschema.Draft202012Validator(schema).iter_errors(instance))
        assert bool(errors) is not case.valid, case.name  # type: ignore[attr-defined]


def set_path(value: object, path: tuple[str | int, ...], replacement: object) -> None:
    current = value
    for part in path[:-1]:
        current = current[part]  # type: ignore[index]
    current[path[-1]] = replacement  # type: ignore[index]


def test_shared_pydantic_json_schema_constraint_matrix(
    document_dict: dict[str, object],
) -> None:
    source_schema = json.loads((SCHEMAS / "source-document.schema.json").read_text())
    identity_schema = json.loads((SCHEMAS / "identity-manifest.schema.json").read_text())
    identity = json.loads((ROOT / ".raptor/identity.json").read_text())
    source_cases: list[tuple[str, dict[str, object]]] = []

    def source_case(name: str, path: tuple[str | int, ...], replacement: object) -> None:
        candidate = deepcopy(document_dict)
        set_path(candidate, path, replacement)
        source_cases.append((name, candidate))

    source_case("unsupported-major-zero", ("schema_version",), "0.9.0")
    source_case("unsupported-major-two", ("schema_version",), "2.0.0")
    source_case("absolute-origin-path", ("provenance", "origin", "initial_repository_path"), "/requirements.md")
    source_case("parent-materialization-path", ("provenance", "materialization", "repository_path"), "../requirements.md")
    source_case("blank-text", ("artifacts", 0, "statement"), "   ")
    source_case("blank-title", ("artifacts", 0, "title"), "   ")
    source_case("extension-key", ("artifacts", 0, "extensions"), {"NotNamespaced": True})
    source_case("relative-uri", ("artifacts", 0, "relationships", 0, "target", "target_uri"), "relative/path")
    source_case("location-missing-end-column", ("artifacts", 0, "source_location"), {"start_line": 1, "start_column": 1, "end_line": 2})
    source_case("location-missing-end-line", ("artifacts", 0, "source_location"), {"start_line": 1, "start_column": 1, "end_column": 2})
    source_case("imported-parent", ("provenance", "materialization", "parent_content_sha256"), "b" * 64)
    source_case("imported-template", ("provenance", "materialization", "template_set"), "templates")

    rendered = deepcopy(document_dict)
    materialization = rendered["provenance"]["materialization"]  # type: ignore[index]
    materialization.update(  # type: ignore[union-attr]
        {
            "operation": "rendered",
            "content_sha256": "b" * 64,
            "parent_content_sha256": "a" * 64,
            "template_set": "templates",
            "template_version": "1.0.0",
        }
    )
    for field in ("parent_content_sha256", "template_set", "template_version"):
        candidate = deepcopy(rendered)
        del candidate["provenance"]["materialization"][field]  # type: ignore[index]
        source_cases.append((f"rendered-missing-{field}", candidate))

    for name, candidate in source_cases:
        with pytest.raises(ValidationError):
            SourceDocument.model_validate(candidate)
        errors = list(jsonschema.Draft202012Validator(source_schema).iter_errors(candidate))
        assert errors, name

    identity_cases = []
    bad_key = deepcopy(identity)
    bad_key["documents"]["BAD"] = bad_key["documents"].pop("DOC-RAP-001")
    identity_cases.append(("identity-document-key", bad_key))
    bad_path = deepcopy(identity)
    bad_path["documents"]["DOC-RAP-001"]["path"] = "../requirements.md"
    identity_cases.append(("identity-path", bad_path))
    for name, candidate in identity_cases:
        with pytest.raises(ValidationError):
            IdentityManifest.model_validate(candidate)
        errors = list(jsonschema.Draft202012Validator(identity_schema).iter_errors(candidate))
        assert errors, name


@pytest.mark.parametrize("field", ["start_line", "start_column", "end_line", "end_column"])
@pytest.mark.parametrize(
    "invalid_value",
    [True, "1", 1.5, 0, -1],
    ids=["bool", "string", "fraction", "zero", "negative"],
)
def test_source_location_integer_constraints_match_pydantic_and_schema(
    document_dict: dict[str, object], field: str, invalid_value: object
) -> None:
    candidate = deepcopy(document_dict)
    location = {
        "start_line": 1,
        "start_column": 1,
        "end_line": 2,
        "end_column": 1,
    }
    location[field] = invalid_value
    set_path(candidate, ("artifacts", 0, "source_location"), location)

    with pytest.raises(ValidationError):
        SourceDocument.model_validate(candidate)
    source_schema = json.loads((SCHEMAS / "source-document.schema.json").read_text())
    errors = list(jsonschema.Draft202012Validator(source_schema).iter_errors(candidate))
    assert errors, (field, invalid_value)
